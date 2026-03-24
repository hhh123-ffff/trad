from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiException
from app.core.logger import logger
from app.models.factor import Factor
from app.models.order import Order
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.price import Price
from app.models.signal import Signal
from app.models.stock import Stock
from app.schemas.backtest import BacktestOverview
from app.schemas.dashboard import DashboardOverview, NavPoint
from app.schemas.order import OrderView
from app.schemas.position import PositionView
from app.schemas.risk import RiskAlert, RiskStatus
from app.schemas.signal import SignalView
from app.services.backtest.engine import get_backtest_overview as load_backtest_overview
from app.services.risk.engine import evaluate_risk_events, list_unresolved_risk_events


def _utc_today() -> date:
    """Return current UTC date."""
    return datetime.now(tz=timezone.utc).date()


def get_dashboard_overview(
    db: Session,
    account_name: str | None = None,
    days: int = 120,
) -> DashboardOverview:
    """Build dashboard summary from current database state with optional account filter."""
    try:
        stock_count = db.scalar(select(func.count(Stock.id))) or 0

        portfolio_stmt = select(Portfolio)
        if account_name:
            portfolio_stmt = portfolio_stmt.where(Portfolio.account_name == account_name)

        latest_portfolio = db.execute(
            portfolio_stmt.order_by(Portfolio.as_of_date.desc()).limit(1)
        ).scalar_one_or_none()

        nav_stmt = select(Portfolio.as_of_date, Portfolio.nav)
        if account_name:
            nav_stmt = nav_stmt.where(Portfolio.account_name == account_name)
        nav_rows = db.execute(
            nav_stmt.order_by(Portfolio.as_of_date.desc()).limit(days)
        ).all()

        nav_series = [NavPoint(trade_date=row[0], nav=float(row[1])) for row in reversed(nav_rows)]

        if latest_portfolio is None:
            return DashboardOverview(
                total_asset=0.0,
                cash=0.0,
                market_value=0.0,
                today_pnl=0.0,
                cumulative_return=0.0,
                position_ratio=0.0,
                max_drawdown=0.0,
                nav_series=nav_series,
                stock_universe_size=int(stock_count),
            )

        return DashboardOverview(
            total_asset=float(latest_portfolio.total_asset),
            cash=float(latest_portfolio.cash),
            market_value=float(latest_portfolio.market_value),
            today_pnl=float(latest_portfolio.daily_pnl),
            cumulative_return=float(latest_portfolio.cumulative_return),
            position_ratio=float(latest_portfolio.position_ratio),
            max_drawdown=float(latest_portfolio.max_drawdown),
            nav_series=nav_series,
            stock_universe_size=int(stock_count),
        )
    except Exception as exc:
        logger.exception("Failed to build dashboard overview: {}", exc)
        raise ApiException(status_code=500, detail="Failed to build dashboard overview.") from exc


def list_positions(
    db: Session,
    account_name: str | None = None,
    snapshot_date: date | None = None,
    symbol: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[PositionView]:
    """Return simulated position snapshot list with filters and pagination."""
    try:
        target_snapshot = snapshot_date
        if target_snapshot is None:
            date_stmt = select(func.max(Position.snapshot_date))
            if account_name:
                date_stmt = date_stmt.where(Position.account_name == account_name)
            target_snapshot = db.scalar(date_stmt)

        if target_snapshot is None:
            return []

        stmt = (
            select(Position, Stock)
            .join(Stock, Stock.id == Position.stock_id)
            .where(
                and_(
                    Position.snapshot_date == target_snapshot,
                    Position.quantity > 0,
                )
            )
            .order_by(Position.market_value.desc())
            .offset(offset)
            .limit(limit)
        )

        if account_name:
            stmt = stmt.where(Position.account_name == account_name)
        if symbol:
            stmt = stmt.where(Stock.symbol == symbol.strip().upper())

        rows = db.execute(stmt).all()

        return [
            PositionView(
                snapshot_date=position.snapshot_date,
                symbol=stock.symbol,
                name=stock.name,
                quantity=int(position.quantity),
                avg_cost=float(position.avg_cost),
                last_price=float(position.last_price),
                market_value=float(position.market_value),
                unrealized_pnl=float(position.unrealized_pnl),
                unrealized_pnl_pct=float(position.unrealized_pnl_pct),
                weight=float(position.weight),
                stop_loss_price=(None if position.stop_loss_price is None else float(position.stop_loss_price)),
            )
            for position, stock in rows
        ]
    except Exception as exc:
        logger.exception("Failed to list positions: {}", exc)
        raise ApiException(status_code=500, detail="Failed to list positions.") from exc


def list_orders(
    db: Session,
    account_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    side: str | None = None,
    symbol: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[OrderView]:
    """Return simulated order history with filters and pagination."""
    try:
        stmt = (
            select(Order, Stock)
            .join(Stock, Stock.id == Order.stock_id)
            .order_by(Order.order_date.desc(), Order.id.desc())
            .offset(offset)
            .limit(limit)
        )

        if account_name:
            stmt = stmt.where(Order.account_name == account_name)
        if date_from:
            stmt = stmt.where(Order.order_date >= date_from)
        if date_to:
            stmt = stmt.where(Order.order_date <= date_to)
        if status:
            stmt = stmt.where(Order.status == status.strip().upper())
        if side:
            stmt = stmt.where(Order.side == side.strip().upper())
        if symbol:
            stmt = stmt.where(Stock.symbol == symbol.strip().upper())

        rows = db.execute(stmt).all()

        return [
            OrderView(
                order_id=int(order.id),
                account_name=order.account_name,
                order_date=order.order_date,
                symbol=stock.symbol,
                side=order.side,
                quantity=int(order.quantity),
                filled_quantity=int(order.filled_quantity),
                price=float(order.price),
                fee=float(order.fee),
                status=order.status,
                note=order.note or "",
            )
            for order, stock in rows
        ]
    except Exception as exc:
        logger.exception("Failed to list orders: {}", exc)
        raise ApiException(status_code=500, detail="Failed to list orders.") from exc


def get_order_by_id(db: Session, order_id: int) -> OrderView | None:
    """Load one order by primary key."""
    try:
        row = db.execute(
            select(Order, Stock)
            .join(Stock, Stock.id == Order.stock_id)
            .where(Order.id == order_id)
        ).first()

        if row is None:
            return None

        order, stock = row
        return OrderView(
            order_id=int(order.id),
            account_name=order.account_name,
            order_date=order.order_date,
            symbol=stock.symbol,
            side=order.side,
            quantity=int(order.quantity),
            filled_quantity=int(order.filled_quantity),
            price=float(order.price),
            fee=float(order.fee),
            status=order.status,
            note=order.note or "",
        )
    except Exception as exc:
        logger.exception("Failed to get order by id: {}", exc)
        raise ApiException(status_code=500, detail="Failed to get order.") from exc


def list_signals(
    db: Session,
    trade_date: date | None = None,
    strategy_name: str | None = None,
    action: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[SignalView]:
    """Return strategy signals with filters and pagination."""
    try:
        target_date = trade_date
        if target_date is None:
            latest_stmt = select(func.max(Signal.trade_date))
            if strategy_name:
                latest_stmt = latest_stmt.where(Signal.strategy_name == strategy_name)
            if action:
                latest_stmt = latest_stmt.where(Signal.action == action.strip().upper())
            target_date = db.scalar(latest_stmt)

        if target_date is None:
            return []

        stmt = (
            select(Signal, Stock, Factor)
            .join(Stock, Stock.id == Signal.stock_id)
            .outerjoin(
                Factor,
                and_(
                    Factor.stock_id == Signal.stock_id,
                    Factor.trade_date == Signal.trade_date,
                ),
            )
            .where(Signal.trade_date == target_date)
            .order_by(Signal.action, Signal.score.desc())
            .offset(offset)
            .limit(limit)
        )

        if strategy_name:
            stmt = stmt.where(Signal.strategy_name == strategy_name)
        if action:
            stmt = stmt.where(Signal.action == action.strip().upper())

        rows = db.execute(stmt).all()

        signals: list[SignalView] = []
        for signal_row, stock_row, factor_row in rows:
            signals.append(
                SignalView(
                    trade_date=signal_row.trade_date,
                    symbol=stock_row.symbol,
                    strategy_name=signal_row.strategy_name,
                    action=signal_row.action,
                    score=float(signal_row.score or 0.0),
                    target_weight=float(signal_row.target_weight or 0.0),
                    reason=signal_row.reason or "",
                    status=signal_row.status,
                    momentum_20=(None if factor_row is None else factor_row.momentum_20),
                    momentum_60=(None if factor_row is None else factor_row.momentum_60),
                    volume_factor=(None if factor_row is None else factor_row.volume_factor),
                    volatility_20=(None if factor_row is None else factor_row.volatility_20),
                    fundamental_factor=(None if factor_row is None else factor_row.fundamental_factor),
                )
            )

        return signals
    except Exception as exc:
        logger.exception("Failed to list signals: {}", exc)
        raise ApiException(status_code=500, detail="Failed to list signals.") from exc


def get_backtest_overview(db: Session, run_id: int | None = None) -> BacktestOverview:
    """Return latest or selected historical backtest overview."""
    try:
        return load_backtest_overview(db=db, run_id=run_id)
    except Exception as exc:
        logger.exception("Failed to build backtest overview: {}", exc)
        raise ApiException(status_code=500, detail="Failed to build backtest overview.") from exc


def get_risk_status(
    db: Session,
    account_name: str | None = None,
) -> RiskStatus:
    """Return current risk status and alerts from live metrics and unresolved risk logs."""
    try:
        target_account = account_name
        if not target_account:
            target_account = db.execute(
                select(Portfolio.account_name)
                .order_by(Portfolio.as_of_date.desc(), Portfolio.id.desc())
                .limit(1)
            ).scalar_one_or_none()

        if not target_account:
            return RiskStatus(
                overall_level="INFO",
                max_drawdown=0.0,
                position_ratio=0.0,
                alerts=[
                    RiskAlert(
                        level="INFO",
                        risk_type="SYSTEM",
                        message="No portfolio snapshot found. Risk check skipped.",
                    )
                ],
            )

        _, position_ratio, max_drawdown, live_events = evaluate_risk_events(
            db=db,
            account_name=target_account,
            as_of_date=None,
            extra_events=None,
        )
        unresolved_events = list_unresolved_risk_events(db=db, account_name=target_account, limit=50)

        merged_events = []
        seen: set[tuple[str, str, str]] = set()
        for event in [*live_events, *unresolved_events]:
            key = (event.level, event.risk_type, event.message)
            if key in seen:
                continue
            seen.add(key)
            merged_events.append(event)

        alerts = [
            RiskAlert(
                level=event.level,
                risk_type=event.risk_type,
                message=event.message,
            )
            for event in merged_events
            if event.level in {"INFO", "WARNING", "CRITICAL"}
        ]

        if not alerts:
            alerts = [
                RiskAlert(
                    level="INFO",
                    risk_type="SYSTEM",
                    message="No active risk alerts.",
                )
            ]

        level_priority = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}
        overall_level = max(alerts, key=lambda item: level_priority.get(item.level, 0)).level

        return RiskStatus(
            overall_level=overall_level,
            max_drawdown=max_drawdown,
            position_ratio=position_ratio,
            alerts=alerts,
        )
    except Exception as exc:
        logger.exception("Failed to build risk status: {}", exc)
        raise ApiException(status_code=500, detail="Failed to build risk status.") from exc
