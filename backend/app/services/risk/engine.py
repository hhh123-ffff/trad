from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logger import logger
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.risk_log import RiskLog
from app.models.stock import Stock


@dataclass
class RiskEvent:
    """One evaluated risk event before persistence."""

    level: str
    risk_type: str
    message: str
    metric_value: float | None = None
    threshold_value: float | None = None


@dataclass
class RiskEvaluationResult:
    """Result returned by risk evaluation and persistence pipeline."""

    risk_date: date
    account_name: str
    position_ratio: float
    max_drawdown: float
    events: list[RiskEvent]
    inserted_count: int
    resolved_count: int


def _utc_today() -> date:
    """Return current UTC date for risk fallback cases."""
    return datetime.now(tz=timezone.utc).date()


def _deduplicate_events(events: list[RiskEvent]) -> list[RiskEvent]:
    """Deduplicate events by semantic fields to avoid repeated log rows."""
    seen: set[tuple[str, str, str, float | None, float | None]] = set()
    result: list[RiskEvent] = []

    for item in events:
        key = (
            item.level,
            item.risk_type,
            item.message,
            None if item.metric_value is None else round(float(item.metric_value), 8),
            None if item.threshold_value is None else round(float(item.threshold_value), 8),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def _resolve_risk_date_portfolio(
    db: Session,
    account_name: str,
    as_of_date: date | None,
) -> Portfolio | None:
    """Resolve latest portfolio snapshot by account and optional upper-bound date."""
    stmt = select(Portfolio).where(Portfolio.account_name == account_name)
    if as_of_date is not None:
        stmt = stmt.where(Portfolio.as_of_date <= as_of_date)

    return db.execute(stmt.order_by(Portfolio.as_of_date.desc()).limit(1)).scalar_one_or_none()


def evaluate_risk_events(
    db: Session,
    account_name: str,
    as_of_date: date | None = None,
    extra_events: list[RiskEvent] | None = None,
) -> tuple[date, float, float, list[RiskEvent]]:
    """Evaluate current portfolio risk events without writing risk logs."""
    settings = get_settings()
    events: list[RiskEvent] = []

    portfolio = _resolve_risk_date_portfolio(db=db, account_name=account_name, as_of_date=as_of_date)
    if portfolio is None:
        events.append(
            RiskEvent(
                level="INFO",
                risk_type="DATA_QUALITY",
                message="No portfolio snapshot found. Risk evaluation skipped.",
            )
        )
        if extra_events:
            events.extend(extra_events)
        deduped = _deduplicate_events(events)
        return (
            as_of_date or _utc_today(),
            0.0,
            0.0,
            deduped,
        )

    risk_date = portfolio.as_of_date
    position_ratio = float(portfolio.position_ratio)
    max_drawdown = float(portfolio.max_drawdown)

    if position_ratio >= settings.risk_max_position_ratio:
        level = "CRITICAL" if position_ratio >= min(1.0, settings.risk_max_position_ratio + 0.05) else "WARNING"
        events.append(
            RiskEvent(
                level=level,
                risk_type="EXPOSURE_LIMIT",
                message=f"Position ratio is {position_ratio:.2%}, exceeded limit {settings.risk_max_position_ratio:.2%}.",
                metric_value=position_ratio,
                threshold_value=settings.risk_max_position_ratio,
            )
        )

    if max_drawdown >= settings.risk_max_drawdown_critical:
        events.append(
            RiskEvent(
                level="CRITICAL",
                risk_type="MAX_DRAWDOWN",
                message=f"Max drawdown is {max_drawdown:.2%}, exceeded critical threshold {settings.risk_max_drawdown_critical:.2%}.",
                metric_value=max_drawdown,
                threshold_value=settings.risk_max_drawdown_critical,
            )
        )
    elif max_drawdown >= settings.risk_max_drawdown_warning:
        events.append(
            RiskEvent(
                level="WARNING",
                risk_type="MAX_DRAWDOWN",
                message=f"Max drawdown is {max_drawdown:.2%}, exceeded warning threshold {settings.risk_max_drawdown_warning:.2%}.",
                metric_value=max_drawdown,
                threshold_value=settings.risk_max_drawdown_warning,
            )
        )

    position_rows = db.execute(
        select(Position, Stock)
        .join(Stock, Stock.id == Position.stock_id)
        .where(
            and_(
                Position.account_name == account_name,
                Position.snapshot_date == risk_date,
                Position.quantity > 0,
            )
        )
    ).all()

    for position, stock in position_rows:
        weight = float(position.weight)
        if weight > settings.risk_single_position_limit:
            events.append(
                RiskEvent(
                    level="WARNING",
                    risk_type="POSITION_LIMIT",
                    message=f"{stock.symbol} weight {weight:.2%} exceeded single-position limit {settings.risk_single_position_limit:.2%}.",
                    metric_value=weight,
                    threshold_value=settings.risk_single_position_limit,
                )
            )

        pnl_pct = float(position.unrealized_pnl_pct)
        if pnl_pct <= settings.risk_stop_loss_pct:
            events.append(
                RiskEvent(
                    level="CRITICAL",
                    risk_type="STOP_LOSS",
                    message=f"{stock.symbol} unrealized PnL {pnl_pct:.2%} breached stop-loss {settings.risk_stop_loss_pct:.2%}.",
                    metric_value=pnl_pct,
                    threshold_value=settings.risk_stop_loss_pct,
                )
            )

    if extra_events:
        events.extend(extra_events)

    deduped = _deduplicate_events(events)
    return (risk_date, position_ratio, max_drawdown, deduped)


def _resolve_inactive_logs(
    db: Session,
    account_name: str,
    risk_date: date,
    active_risk_types: set[str],
) -> int:
    """Resolve obsolete unresolved logs when the related risk type is no longer active."""
    controllable_types = {"POSITION_LIMIT", "STOP_LOSS", "MAX_DRAWDOWN", "EXPOSURE_LIMIT"}
    rows = db.execute(
        select(RiskLog).where(
            and_(
                RiskLog.account_name == account_name,
                RiskLog.resolved.is_(False),
                RiskLog.risk_date < risk_date,
                RiskLog.risk_type.in_(controllable_types),
            )
        )
    ).scalars().all()

    resolved_count = 0
    for row in rows:
        if row.risk_type in active_risk_types:
            continue
        row.resolved = True
        resolved_count += 1

    return resolved_count


def _persist_risk_events(
    db: Session,
    account_name: str,
    risk_date: date,
    events: list[RiskEvent],
) -> int:
    """Persist risk events to risk_logs with duplication guard."""
    inserted = 0

    for event in events:
        exists = db.execute(
            select(RiskLog.id).where(
                and_(
                    RiskLog.risk_date == risk_date,
                    RiskLog.account_name == account_name,
                    RiskLog.risk_type == event.risk_type,
                    RiskLog.level == event.level,
                    RiskLog.message == event.message,
                    RiskLog.resolved.is_(False),
                )
            )
        ).scalar_one_or_none()

        if exists is not None:
            continue

        db.add(
            RiskLog(
                risk_date=risk_date,
                account_name=account_name,
                risk_type=event.risk_type,
                level=event.level,
                message=event.message,
                metric_value=event.metric_value,
                threshold_value=event.threshold_value,
                resolved=False,
            )
        )
        inserted += 1

    return inserted


def evaluate_and_log_risk_events(
    db: Session,
    account_name: str,
    as_of_date: date | None = None,
    extra_events: list[RiskEvent] | None = None,
) -> RiskEvaluationResult:
    """Evaluate account risk and persist events into risk_logs table."""
    risk_date, position_ratio, max_drawdown, events = evaluate_risk_events(
        db=db,
        account_name=account_name,
        as_of_date=as_of_date,
        extra_events=extra_events,
    )

    active_risk_types = {item.risk_type for item in events if item.level in {"WARNING", "CRITICAL"}}
    resolved_count = _resolve_inactive_logs(
        db=db,
        account_name=account_name,
        risk_date=risk_date,
        active_risk_types=active_risk_types,
    )
    inserted_count = _persist_risk_events(
        db=db,
        account_name=account_name,
        risk_date=risk_date,
        events=events,
    )

    result = RiskEvaluationResult(
        risk_date=risk_date,
        account_name=account_name,
        position_ratio=position_ratio,
        max_drawdown=max_drawdown,
        events=events,
        inserted_count=inserted_count,
        resolved_count=resolved_count,
    )
    logger.info(
        "Risk evaluation completed: account={} date={} events={} inserted={} resolved={}",
        account_name,
        risk_date,
        len(events),
        inserted_count,
        resolved_count,
    )
    return result


def list_unresolved_risk_events(
    db: Session,
    account_name: str,
    limit: int = 50,
) -> list[RiskEvent]:
    """Load unresolved risk logs and convert them to runtime risk events."""
    rows = db.execute(
        select(RiskLog)
        .where(
            and_(
                RiskLog.account_name == account_name,
                RiskLog.resolved.is_(False),
            )
        )
        .order_by(RiskLog.risk_date.desc(), RiskLog.id.desc())
        .limit(limit)
    ).scalars().all()

    return [
        RiskEvent(
            level=row.level,
            risk_type=row.risk_type,
            message=row.message,
            metric_value=(None if row.metric_value is None else float(row.metric_value)),
            threshold_value=(None if row.threshold_value is None else float(row.threshold_value)),
        )
        for row in rows
    ]
