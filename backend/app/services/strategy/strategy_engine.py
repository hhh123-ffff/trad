from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logger import logger
from app.models.factor import Factor
from app.models.price import Price
from app.models.signal import Signal
from app.models.stock import Stock
from app.services.strategy.factor_engine import FactorEngine


@dataclass
class StrategyRunResult:
    """Summary of one strategy signal generation run."""

    trade_date: date
    strategy_name: str
    status: str
    timing_passed: bool
    reason: str
    selected_count: int
    buy_count: int
    sell_count: int
    hold_count: int


def _is_rebalance_day(trade_date: date, target_weekday: int) -> bool:
    """Check whether trade date matches configured rebalance weekday."""
    return trade_date.weekday() == target_weekday


def _get_latest_factor_date(db: Session, factor_version: str) -> date | None:
    """Get latest available factor trade date."""
    return db.scalar(select(func.max(Factor.trade_date)).where(Factor.factor_version == factor_version))


def _get_top_factors(db: Session, trade_date: date, factor_version: str, top_n: int) -> list[tuple[Factor, Stock]]:
    """Get top-N stocks by total factor score on target date."""
    rows = (
        db.execute(
            select(Factor, Stock)
            .join(Stock, Stock.id == Factor.stock_id)
            .where(
                and_(
                    Factor.trade_date == trade_date,
                    Factor.factor_version == factor_version,
                    Factor.total_score.is_not(None),
                )
            )
            .order_by(Factor.total_score.desc())
            .limit(top_n)
        )
        .all()
    )
    return rows


def _get_previous_selected_ids(db: Session, strategy_name: str, trade_date: date) -> set[int]:
    """Load previous rebalance selected holdings from latest strategy signal date."""
    previous_date = db.scalar(
        select(func.max(Signal.trade_date)).where(and_(Signal.strategy_name == strategy_name, Signal.trade_date < trade_date))
    )
    if previous_date is None:
        return set()

    rows = db.execute(
        select(Signal.stock_id).where(
            and_(
                Signal.strategy_name == strategy_name,
                Signal.trade_date == previous_date,
                Signal.action.in_(["BUY", "HOLD"]),
                Signal.target_weight.is_not(None),
                Signal.target_weight > 0,
            )
        )
    ).all()
    return {int(row[0]) for row in rows}


def _evaluate_market_timing(db: Session, benchmark_symbol: str, trade_date: date, ma_window: int) -> tuple[bool, str]:
    """Evaluate benchmark MA timing filter using latest close versus moving average."""
    benchmark_id = db.scalar(select(Stock.id).where(Stock.symbol == benchmark_symbol))
    if benchmark_id is None:
        return (True, "Benchmark data not found. Timing filter skipped.")

    rows = db.execute(
        select(Price.trade_date, Price.close)
        .where(and_(Price.stock_id == benchmark_id, Price.trade_date <= trade_date))
        .order_by(Price.trade_date.desc())
        .limit(ma_window)
    ).all()

    if len(rows) < ma_window:
        return (True, "Benchmark data insufficient for MA filter. Timing filter skipped.")

    closes_desc = [float(row[1]) for row in rows]
    latest_close = closes_desc[0]
    moving_average = sum(closes_desc) / len(closes_desc)

    if latest_close >= moving_average:
        return (True, f"Timing passed: benchmark close {latest_close:.4f} >= MA{ma_window} {moving_average:.4f}.")
    return (False, f"Timing blocked: benchmark close {latest_close:.4f} < MA{ma_window} {moving_average:.4f}.")


def _upsert_signal(
    db: Session,
    trade_date: date,
    stock_id: int,
    strategy_name: str,
    action: str,
    score: float | None,
    target_weight: float,
    reason: str,
) -> None:
    """Insert or update one strategy signal row."""
    existing = db.execute(
        select(Signal).where(
            and_(
                Signal.trade_date == trade_date,
                Signal.stock_id == stock_id,
                Signal.strategy_name == strategy_name,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(
            Signal(
                trade_date=trade_date,
                stock_id=stock_id,
                strategy_name=strategy_name,
                action=action,
                score=score,
                target_weight=target_weight,
                reason=reason,
                status="NEW",
            )
        )
        return

    existing.action = action
    existing.score = score
    existing.target_weight = target_weight
    existing.reason = reason
    existing.status = "NEW"


class MultiFactorStrategyEngine:
    """Multi-factor strategy engine with weekly rebalance and timing filter."""

    def __init__(self, factor_engine: FactorEngine | None = None) -> None:
        """Initialize strategy engine with factor engine dependency."""
        self.factor_engine = factor_engine or FactorEngine()

    def run(
        self,
        db: Session,
        trade_date: date | None = None,
        top_n: int | None = None,
        strategy_name: str | None = None,
        factor_version: str = "v1",
        force_rebalance: bool = False,
    ) -> StrategyRunResult:
        """Run factor + strategy pipeline and persist generated signals."""
        settings = get_settings()
        final_strategy_name = strategy_name or settings.strategy_name
        final_top_n = top_n or settings.strategy_top_n

        final_trade_date = trade_date or _get_latest_factor_date(db, factor_version=factor_version)
        if final_trade_date is None:
            lookback_end = date.today()
            lookback_start = lookback_end - timedelta(days=180)
            self.factor_engine.run(
                db=db,
                start_date=lookback_start,
                end_date=lookback_end,
                symbols=None,
                factor_version=factor_version,
            )
            final_trade_date = _get_latest_factor_date(db, factor_version=factor_version)

        if final_trade_date is None:
            return StrategyRunResult(
                trade_date=date.today(),
                strategy_name=final_strategy_name,
                status="SKIPPED",
                timing_passed=True,
                reason="No factor data available.",
                selected_count=0,
                buy_count=0,
                sell_count=0,
                hold_count=0,
            )

        if not force_rebalance and not _is_rebalance_day(final_trade_date, settings.rebalance_weekday):
            return StrategyRunResult(
                trade_date=final_trade_date,
                strategy_name=final_strategy_name,
                status="SKIPPED",
                timing_passed=True,
                reason=f"Not rebalance day. weekday={final_trade_date.weekday()} expected={settings.rebalance_weekday}.",
                selected_count=0,
                buy_count=0,
                sell_count=0,
                hold_count=0,
            )

        try:
            timing_passed, timing_reason = _evaluate_market_timing(
                db=db,
                benchmark_symbol=settings.benchmark_symbol,
                trade_date=final_trade_date,
                ma_window=settings.timing_ma_window,
            )

            top_rows = _get_top_factors(
                db=db,
                trade_date=final_trade_date,
                factor_version=factor_version,
                top_n=final_top_n,
            )

            current_ids = {int(row[0].stock_id) for row in top_rows} if timing_passed else set()
            score_map = {int(row[0].stock_id): float(row[0].total_score or 0.0) for row in top_rows}

            previous_ids = _get_previous_selected_ids(
                db=db,
                strategy_name=final_strategy_name,
                trade_date=final_trade_date,
            )

            buy_ids = current_ids - previous_ids
            sell_ids = previous_ids - current_ids
            hold_ids = current_ids & previous_ids

            target_weight = (1.0 / len(current_ids)) if current_ids else 0.0

            for stock_id in sorted(buy_ids):
                _upsert_signal(
                    db=db,
                    trade_date=final_trade_date,
                    stock_id=stock_id,
                    strategy_name=final_strategy_name,
                    action="BUY",
                    score=score_map.get(stock_id),
                    target_weight=target_weight,
                    reason=f"Selected by top-N factor ranking. {timing_reason}",
                )

            for stock_id in sorted(hold_ids):
                _upsert_signal(
                    db=db,
                    trade_date=final_trade_date,
                    stock_id=stock_id,
                    strategy_name=final_strategy_name,
                    action="HOLD",
                    score=score_map.get(stock_id),
                    target_weight=target_weight,
                    reason=f"Remain in portfolio after rebalance. {timing_reason}",
                )

            for stock_id in sorted(sell_ids):
                _upsert_signal(
                    db=db,
                    trade_date=final_trade_date,
                    stock_id=stock_id,
                    strategy_name=final_strategy_name,
                    action="SELL",
                    score=score_map.get(stock_id),
                    target_weight=0.0,
                    reason=f"Removed during rebalance. {timing_reason}",
                )

            db.commit()

            result = StrategyRunResult(
                trade_date=final_trade_date,
                strategy_name=final_strategy_name,
                status="SUCCESS",
                timing_passed=timing_passed,
                reason=timing_reason,
                selected_count=len(current_ids),
                buy_count=len(buy_ids),
                sell_count=len(sell_ids),
                hold_count=len(hold_ids),
            )
            logger.info("Strategy engine completed: {}", result)
            return result
        except Exception as exc:
            db.rollback()
            logger.exception("Strategy engine execution failed: {}", exc)
            raise
