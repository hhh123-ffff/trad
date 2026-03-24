from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logger import logger
from app.models.order import Order
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.price import Price
from app.models.signal import Signal
from app.models.stock import Stock
from app.services.risk.engine import RiskEvent, evaluate_and_log_risk_events


@dataclass
class HoldingState:
    """In-memory holding state used during one simulation run."""

    quantity: int
    avg_cost: float


@dataclass
class SimulationResult:
    """Summary result of one paper trading simulation run."""

    account_name: str
    trade_date: date
    signal_count: int
    orders_created: int
    buy_count: int
    sell_count: int
    rejected_count: int
    holding_count: int
    cash: float
    market_value: float
    total_asset: float
    position_ratio: float


def _get_run_date(db: Session, run_date: date | None) -> date:
    """Resolve simulation run date with latest available signal date fallback."""
    if run_date is not None:
        return run_date

    latest_date = db.scalar(select(func.max(Signal.trade_date)))
    if latest_date is None:
        raise RuntimeError("No signals available for simulation.")
    return latest_date


def _get_previous_portfolio(db: Session, account_name: str, run_date: date) -> Portfolio | None:
    """Load latest portfolio snapshot before run date."""
    return db.execute(
        select(Portfolio)
        .where(
            and_(
                Portfolio.account_name == account_name,
                Portfolio.as_of_date < run_date,
            )
        )
        .order_by(Portfolio.as_of_date.desc())
        .limit(1)
    ).scalar_one_or_none()


def _get_previous_holdings(db: Session, account_name: str, run_date: date) -> dict[int, HoldingState]:
    """Load previous day holdings as initial simulation state."""
    latest_snapshot = db.scalar(
        select(func.max(Position.snapshot_date)).where(
            and_(
                Position.account_name == account_name,
                Position.snapshot_date < run_date,
            )
        )
    )
    if latest_snapshot is None:
        return {}

    rows = db.execute(
        select(Position)
        .where(
            and_(
                Position.account_name == account_name,
                Position.snapshot_date == latest_snapshot,
                Position.quantity > 0,
            )
        )
    ).scalars().all()

    return {
        int(row.stock_id): HoldingState(quantity=int(row.quantity), avg_cost=float(row.avg_cost))
        for row in rows
    }


def _get_price_map(db: Session, stock_ids: set[int], run_date: date) -> dict[int, float]:
    """Load close price map for target date and stock set."""
    if not stock_ids:
        return {}

    rows = db.execute(
        select(Price.stock_id, Price.close)
        .where(
            and_(
                Price.trade_date == run_date,
                Price.stock_id.in_(stock_ids),
            )
        )
    ).all()
    price_map = {int(row[0]): float(row[1]) for row in rows}

    missing = [stock_id for stock_id in stock_ids if stock_id not in price_map]
    if missing:
        fallback_rows = db.execute(
            select(Price.stock_id, func.max(Price.trade_date))
            .where(
                and_(
                    Price.stock_id.in_(missing),
                    Price.trade_date < run_date,
                )
            )
            .group_by(Price.stock_id)
        ).all()
        for stock_id, fallback_date in fallback_rows:
            close_price = db.scalar(
                select(Price.close).where(
                    and_(
                        Price.stock_id == stock_id,
                        Price.trade_date == fallback_date,
                    )
                )
            )
            if close_price is not None:
                price_map[int(stock_id)] = float(close_price)

    return price_map


def _get_symbol_map(db: Session, stock_ids: set[int]) -> dict[int, str]:
    """Load stock symbol map by stock id."""
    if not stock_ids:
        return {}

    rows = db.execute(select(Stock.id, Stock.symbol).where(Stock.id.in_(stock_ids))).all()
    return {int(row[0]): str(row[1]) for row in rows}


def _upsert_position_snapshot(
    db: Session,
    account_name: str,
    run_date: date,
    stock_id: int,
    holding: HoldingState,
    price: float,
    total_asset: float,
) -> None:
    """Insert or update one position snapshot row."""
    market_value = holding.quantity * price
    unrealized_pnl = (price - holding.avg_cost) * holding.quantity
    unrealized_pnl_pct = 0.0 if holding.avg_cost <= 0 else (price / holding.avg_cost - 1.0)
    weight = 0.0 if total_asset <= 0 else market_value / total_asset

    existing = db.execute(
        select(Position).where(
            and_(
                Position.account_name == account_name,
                Position.stock_id == stock_id,
                Position.snapshot_date == run_date,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(
            Position(
                account_name=account_name,
                stock_id=stock_id,
                snapshot_date=run_date,
                quantity=holding.quantity,
                available_quantity=holding.quantity,
                avg_cost=holding.avg_cost,
                last_price=price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                weight=weight,
                stop_loss_price=holding.avg_cost * 0.92,
                status="OPEN",
            )
        )
        return

    existing.quantity = holding.quantity
    existing.available_quantity = holding.quantity
    existing.avg_cost = holding.avg_cost
    existing.last_price = price
    existing.market_value = market_value
    existing.unrealized_pnl = unrealized_pnl
    existing.unrealized_pnl_pct = unrealized_pnl_pct
    existing.weight = weight
    existing.stop_loss_price = holding.avg_cost * 0.92
    existing.status = "OPEN"


def _upsert_portfolio_snapshot(
    db: Session,
    account_name: str,
    run_date: date,
    cash: float,
    market_value: float,
    total_asset: float,
    daily_pnl: float,
    cumulative_return: float,
    nav: float,
    position_ratio: float,
    max_drawdown: float,
) -> None:
    """Insert or update one portfolio snapshot row."""
    existing = db.execute(
        select(Portfolio).where(
            and_(
                Portfolio.account_name == account_name,
                Portfolio.as_of_date == run_date,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(
            Portfolio(
                account_name=account_name,
                as_of_date=run_date,
                cash=cash,
                market_value=market_value,
                total_asset=total_asset,
                daily_pnl=daily_pnl,
                cumulative_return=cumulative_return,
                nav=nav,
                position_ratio=position_ratio,
                max_drawdown=max_drawdown,
            )
        )
        return

    existing.cash = cash
    existing.market_value = market_value
    existing.total_asset = total_asset
    existing.daily_pnl = daily_pnl
    existing.cumulative_return = cumulative_return
    existing.nav = nav
    existing.position_ratio = position_ratio
    existing.max_drawdown = max_drawdown


def _save_order(
    db: Session,
    account_name: str,
    signal: Signal,
    side: str,
    price: float,
    quantity: int,
    filled_quantity: int,
    fee: float,
    status: str,
    note: str,
) -> None:
    """Persist one simulated order row tied to one strategy signal."""
    db.add(
        Order(
            account_name=account_name,
            signal_id=signal.id,
            stock_id=signal.stock_id,
            order_date=signal.trade_date,
            side=side,
            order_type="SIM",
            price=price,
            quantity=quantity,
            filled_quantity=filled_quantity,
            fee=fee,
            status=status,
            note=note,
        )
    )


def _save_risk_order(
    db: Session,
    account_name: str,
    stock_id: int,
    trade_date: date,
    side: str,
    price: float,
    quantity: int,
    filled_quantity: int,
    fee: float,
    status: str,
    note: str,
) -> None:
    """Persist one simulated order row triggered by risk control instead of strategy signal."""
    db.add(
        Order(
            account_name=account_name,
            signal_id=None,
            stock_id=stock_id,
            order_date=trade_date,
            side=side,
            order_type="SIM",
            price=price,
            quantity=quantity,
            filled_quantity=filled_quantity,
            fee=fee,
            status=status,
            note=note,
        )
    )


def _mark_signal_status(signal: Signal, status: str) -> None:
    """Update signal status field in memory."""
    signal.status = status


class PaperTradingEngine:
    """Paper trading engine that converts signals to simulated portfolio changes."""

    def run(
        self,
        db: Session,
        run_date: date | None = None,
        account_name: str | None = None,
    ) -> SimulationResult:
        """Execute one-day paper trading simulation based on generated signals."""
        settings = get_settings()
        final_account = account_name or settings.default_account
        final_date = _get_run_date(db=db, run_date=run_date)

        try:
            signals = db.execute(
                select(Signal)
                .where(Signal.trade_date == final_date)
                .order_by(
                    Signal.action.desc(),
                    Signal.score.desc(),
                )
            ).scalars().all()

            if not signals:
                raise RuntimeError(f"No signals found on trade date {final_date}.")

            previous_portfolio = _get_previous_portfolio(db=db, account_name=final_account, run_date=final_date)
            holdings = _get_previous_holdings(db=db, account_name=final_account, run_date=final_date)

            cash = settings.initial_capital if previous_portfolio is None else float(previous_portfolio.cash)
            previous_total_asset = settings.initial_capital if previous_portfolio is None else float(previous_portfolio.total_asset)

            stock_ids = {int(signal.stock_id) for signal in signals} | set(holdings.keys())
            price_map = _get_price_map(db=db, stock_ids=stock_ids, run_date=final_date)
            symbol_map = _get_symbol_map(db=db, stock_ids=stock_ids)

            runtime_risk_events: list[RiskEvent] = []

            buy_count = 0
            sell_count = 0
            rejected_count = 0
            orders_created = 0

            for stock_id, holding in list(holdings.items()):
                price = price_map.get(stock_id)
                if price is None or price <= 0 or holding.quantity <= 0 or holding.avg_cost <= 0:
                    continue

                pnl_pct = price / holding.avg_cost - 1.0
                if pnl_pct > settings.risk_stop_loss_pct:
                    continue

                gross = holding.quantity * price
                fee = gross * settings.trade_fee_rate
                net = gross - fee
                cash += net

                symbol = symbol_map.get(stock_id, str(stock_id))
                note = (
                    f"Auto stop-loss triggered for {symbol}: pnl {pnl_pct:.2%} <= "
                    f"threshold {settings.risk_stop_loss_pct:.2%}."
                )
                _save_risk_order(
                    db=db,
                    account_name=final_account,
                    stock_id=stock_id,
                    trade_date=final_date,
                    side="SELL",
                    price=price,
                    quantity=holding.quantity,
                    filled_quantity=holding.quantity,
                    fee=fee,
                    status="FILLED",
                    note=note,
                )
                runtime_risk_events.append(
                    RiskEvent(
                        level="CRITICAL",
                        risk_type="STOP_LOSS",
                        message=note,
                        metric_value=float(pnl_pct),
                        threshold_value=float(settings.risk_stop_loss_pct),
                    )
                )

                del holdings[stock_id]
                sell_count += 1
                orders_created += 1

            sell_signals = [signal for signal in signals if signal.action == "SELL"]
            other_signals = [signal for signal in signals if signal.action != "SELL"]

            for signal in sell_signals:
                stock_id = int(signal.stock_id)
                holding = holdings.get(stock_id)
                price = price_map.get(stock_id)

                if holding is None or holding.quantity <= 0:
                    _save_order(
                        db=db,
                        account_name=final_account,
                        signal=signal,
                        side="SELL",
                        price=0.0 if price is None else price,
                        quantity=0,
                        filled_quantity=0,
                        fee=0.0,
                        status="REJECTED",
                        note="No existing position to sell.",
                    )
                    _mark_signal_status(signal, "CANCELLED")
                    rejected_count += 1
                    orders_created += 1
                    continue

                if price is None or price <= 0:
                    _save_order(
                        db=db,
                        account_name=final_account,
                        signal=signal,
                        side="SELL",
                        price=0.0,
                        quantity=holding.quantity,
                        filled_quantity=0,
                        fee=0.0,
                        status="REJECTED",
                        note="No valid market price available.",
                    )
                    _mark_signal_status(signal, "CANCELLED")
                    rejected_count += 1
                    orders_created += 1
                    continue

                gross = holding.quantity * price
                fee = gross * settings.trade_fee_rate
                net = gross - fee
                cash += net

                _save_order(
                    db=db,
                    account_name=final_account,
                    signal=signal,
                    side="SELL",
                    price=price,
                    quantity=holding.quantity,
                    filled_quantity=holding.quantity,
                    fee=fee,
                    status="FILLED",
                    note="Filled by simulation engine.",
                )
                _mark_signal_status(signal, "EXECUTED")
                del holdings[stock_id]
                sell_count += 1
                orders_created += 1

            market_value_pre = sum(
                holdings[stock_id].quantity * price_map.get(stock_id, holdings[stock_id].avg_cost)
                for stock_id in holdings
            )
            total_asset_for_target = cash + market_value_pre
            max_market_value_allowed = total_asset_for_target * settings.risk_max_position_ratio
            single_position_cap_value = total_asset_for_target * settings.risk_single_position_limit
            market_value_live = market_value_pre

            for signal in other_signals:
                if signal.action != "BUY":
                    _mark_signal_status(signal, "EXECUTED")
                    continue

                stock_id = int(signal.stock_id)
                price = price_map.get(stock_id)
                target_weight = float(signal.target_weight or 0.0)

                if price is None or price <= 0:
                    _save_order(
                        db=db,
                        account_name=final_account,
                        signal=signal,
                        side="BUY",
                        price=0.0,
                        quantity=0,
                        filled_quantity=0,
                        fee=0.0,
                        status="REJECTED",
                        note="No valid market price available.",
                    )
                    _mark_signal_status(signal, "CANCELLED")
                    rejected_count += 1
                    orders_created += 1
                    continue

                current_holding = holdings.get(stock_id, HoldingState(quantity=0, avg_cost=price))
                current_value = current_holding.quantity * price
                target_value_raw = total_asset_for_target * max(target_weight, 0.0)
                target_value = min(target_value_raw, single_position_cap_value)

                if target_value_raw > target_value:
                    symbol = symbol_map.get(stock_id, str(stock_id))
                    runtime_risk_events.append(
                        RiskEvent(
                            level="WARNING",
                            risk_type="POSITION_LIMIT",
                            message=(
                                f"{symbol} target value {target_value_raw:.2f} exceeded single-position cap "
                                f"{single_position_cap_value:.2f}; capped during order sizing."
                            ),
                            metric_value=float(target_value_raw / total_asset_for_target) if total_asset_for_target > 0 else None,
                            threshold_value=float(settings.risk_single_position_limit),
                        )
                    )

                budget = target_value - current_value
                exposure_remaining = max_market_value_allowed - market_value_live
                budget = min(budget, exposure_remaining)

                if budget <= 0:
                    _save_order(
                        db=db,
                        account_name=final_account,
                        signal=signal,
                        side="BUY",
                        price=price,
                        quantity=0,
                        filled_quantity=0,
                        fee=0.0,
                        status="REJECTED",
                        note="Exposure limit reached or target allocation already satisfied.",
                    )
                    _mark_signal_status(signal, "CANCELLED")
                    rejected_count += 1
                    orders_created += 1

                    symbol = symbol_map.get(stock_id, str(stock_id))
                    runtime_risk_events.append(
                        RiskEvent(
                            level="WARNING",
                            risk_type="EXPOSURE_LIMIT",
                            message=(
                                f"{symbol} buy request rejected due to exposure control. "
                                f"Max position ratio {settings.risk_max_position_ratio:.2%}."
                            ),
                            metric_value=float(market_value_live / total_asset_for_target) if total_asset_for_target > 0 else None,
                            threshold_value=float(settings.risk_max_position_ratio),
                        )
                    )
                    continue

                quantity = int((budget / price) // settings.min_trade_lot * settings.min_trade_lot)
                affordable_quantity = int((cash / (price * (1 + settings.trade_fee_rate))) // settings.min_trade_lot * settings.min_trade_lot)
                quantity = min(quantity, affordable_quantity)

                if quantity <= 0:
                    _save_order(
                        db=db,
                        account_name=final_account,
                        signal=signal,
                        side="BUY",
                        price=price,
                        quantity=0,
                        filled_quantity=0,
                        fee=0.0,
                        status="REJECTED",
                        note="Insufficient cash for minimum trade lot.",
                    )
                    _mark_signal_status(signal, "CANCELLED")
                    rejected_count += 1
                    orders_created += 1
                    continue

                gross = quantity * price
                fee = gross * settings.trade_fee_rate
                total_cost = gross + fee
                cash -= total_cost
                market_value_live += gross

                new_quantity = current_holding.quantity + quantity
                new_avg_cost = (
                    (current_holding.avg_cost * current_holding.quantity + gross) / new_quantity
                    if new_quantity > 0
                    else price
                )
                holdings[stock_id] = HoldingState(quantity=new_quantity, avg_cost=float(new_avg_cost))

                _save_order(
                    db=db,
                    account_name=final_account,
                    signal=signal,
                    side="BUY",
                    price=price,
                    quantity=quantity,
                    filled_quantity=quantity,
                    fee=fee,
                    status="FILLED",
                    note="Filled by simulation engine.",
                )
                _mark_signal_status(signal, "EXECUTED")
                buy_count += 1
                orders_created += 1

            market_value = 0.0
            for stock_id, holding in holdings.items():
                price = price_map.get(stock_id, holding.avg_cost)
                market_value += holding.quantity * price

            total_asset = cash + market_value
            position_ratio = 0.0 if total_asset <= 0 else market_value / total_asset

            for stock_id, holding in holdings.items():
                price = price_map.get(stock_id, holding.avg_cost)
                _upsert_position_snapshot(
                    db=db,
                    account_name=final_account,
                    run_date=final_date,
                    stock_id=stock_id,
                    holding=holding,
                    price=price,
                    total_asset=total_asset,
                )

            previous_peak_nav = db.scalar(
                select(func.max(Portfolio.nav)).where(Portfolio.account_name == final_account)
            )
            nav = 0.0 if settings.initial_capital <= 0 else total_asset / settings.initial_capital
            peak_nav = nav if previous_peak_nav is None else max(float(previous_peak_nav), nav)
            current_drawdown = 0.0 if peak_nav <= 0 else max(0.0, 1.0 - nav / peak_nav)
            previous_max_drawdown = db.scalar(
                select(func.max(Portfolio.max_drawdown)).where(Portfolio.account_name == final_account)
            )
            max_drawdown = current_drawdown if previous_max_drawdown is None else max(float(previous_max_drawdown), current_drawdown)

            daily_pnl = total_asset - previous_total_asset
            cumulative_return = 0.0 if settings.initial_capital <= 0 else total_asset / settings.initial_capital - 1.0

            _upsert_portfolio_snapshot(
                db=db,
                account_name=final_account,
                run_date=final_date,
                cash=cash,
                market_value=market_value,
                total_asset=total_asset,
                daily_pnl=daily_pnl,
                cumulative_return=cumulative_return,
                nav=nav,
                position_ratio=position_ratio,
                max_drawdown=max_drawdown,
            )

            evaluate_and_log_risk_events(
                db=db,
                account_name=final_account,
                as_of_date=final_date,
                extra_events=runtime_risk_events,
            )

            db.commit()

            result = SimulationResult(
                account_name=final_account,
                trade_date=final_date,
                signal_count=len(signals),
                orders_created=orders_created,
                buy_count=buy_count,
                sell_count=sell_count,
                rejected_count=rejected_count,
                holding_count=len(holdings),
                cash=round(float(cash), 2),
                market_value=round(float(market_value), 2),
                total_asset=round(float(total_asset), 2),
                position_ratio=round(float(position_ratio), 6),
            )
            logger.info("Paper trading simulation completed: {}", result)
            return result
        except Exception as exc:
            db.rollback()
            logger.exception("Paper trading simulation failed: {}", exc)
            raise
