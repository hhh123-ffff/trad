from datetime import date

from sqlalchemy import and_, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.order import Order
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.price import Price
from app.models.risk_log import RiskLog
from app.models.signal import Signal
from app.models.stock import Stock


def _seed_stock(db, symbol: str, exchange: str = "SSE") -> Stock:
    """Create one stock row and return persisted ORM object."""
    stock = Stock(
        symbol=symbol,
        name=f"Stock-{symbol}",
        exchange=exchange,
        status="ACTIVE",
    )
    db.add(stock)
    db.flush()
    return stock


def _seed_price(db, stock_id: int, trade_date: date, close: float) -> None:
    """Create one daily price row with simple OHLC values."""
    db.add(
        Price(
            stock_id=stock_id,
            trade_date=trade_date,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1_000_000,
            amount=close * 1_000_000,
        )
    )


def test_stop_loss_auto_sell_and_log(client) -> None:
    """Stop-loss breach should force a sell and persist STOP_LOSS risk log."""
    account_name = "risk_stop_account"
    prev_date = date(2024, 4, 29)
    run_date = date(2024, 4, 30)

    db = SessionLocal()
    try:
        stock = _seed_stock(db, "600001.SH")

        db.add(
            Portfolio(
                account_name=account_name,
                as_of_date=prev_date,
                cash=999_000.0,
                market_value=1_000.0,
                total_asset=1_000_000.0,
                daily_pnl=0.0,
                cumulative_return=0.0,
                nav=1.0,
                position_ratio=0.001,
                max_drawdown=0.02,
            )
        )
        db.add(
            Position(
                account_name=account_name,
                stock_id=stock.id,
                snapshot_date=prev_date,
                quantity=100,
                available_quantity=100,
                avg_cost=10.0,
                last_price=10.0,
                market_value=1_000.0,
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0,
                weight=0.001,
                stop_loss_price=9.2,
                status="OPEN",
            )
        )
        _seed_price(db, stock.id, run_date, close=9.0)
        db.add(
            Signal(
                trade_date=run_date,
                stock_id=stock.id,
                strategy_name="multi_factor_v1",
                action="HOLD",
                score=0.0,
                target_weight=0.0,
                reason="Keep position.",
                status="NEW",
            )
        )
        db.commit()
    finally:
        db.close()

    run_resp = client.post(
        "/api/v1/simulation/run",
        json={
            "trade_date": "2024-04-30",
            "account_name": account_name,
        },
    )
    assert run_resp.status_code == 200
    assert run_resp.json()["sell_count"] >= 1

    db = SessionLocal()
    try:
        stop_order = db.execute(
            select(Order).where(
                and_(
                    Order.account_name == account_name,
                    Order.side == "SELL",
                    Order.status == "FILLED",
                    Order.note.like("%Auto stop-loss triggered%"),
                )
            )
        ).scalar_one_or_none()
        assert stop_order is not None

        risk_logs = db.execute(
            select(RiskLog).where(
                and_(
                    RiskLog.account_name == account_name,
                    RiskLog.risk_type == "STOP_LOSS",
                    RiskLog.resolved.is_(False),
                )
            )
        ).scalars().all()
        assert len(risk_logs) >= 1
    finally:
        db.close()

    risk_resp = client.get(f"/api/v1/risk?account_name={account_name}")
    assert risk_resp.status_code == 200
    assert any(item["risk_type"] == "STOP_LOSS" for item in risk_resp.json()["alerts"])


def test_exposure_limit_rejects_buy_and_records_risk(client, monkeypatch) -> None:
    """Low exposure cap should reject buy orders and emit EXPOSURE_LIMIT risk log."""
    account_name = "risk_exposure_account"
    prev_date = date(2024, 4, 29)
    run_date = date(2024, 4, 30)

    monkeypatch.setenv("RISK_MAX_POSITION_RATIO", "0.20")
    get_settings.cache_clear()

    try:
        db = SessionLocal()
        try:
            hold_stock = _seed_stock(db, "600002.SH")
            buy_stock = _seed_stock(db, "600003.SH")

            db.add(
                Portfolio(
                    account_name=account_name,
                    as_of_date=prev_date,
                    cash=100_000.0,
                    market_value=900_000.0,
                    total_asset=1_000_000.0,
                    daily_pnl=0.0,
                    cumulative_return=0.0,
                    nav=1.0,
                    position_ratio=0.9,
                    max_drawdown=0.02,
                )
            )
            db.add(
                Position(
                    account_name=account_name,
                    stock_id=hold_stock.id,
                    snapshot_date=prev_date,
                    quantity=90_000,
                    available_quantity=90_000,
                    avg_cost=10.0,
                    last_price=10.0,
                    market_value=900_000.0,
                    unrealized_pnl=0.0,
                    unrealized_pnl_pct=0.0,
                    weight=0.9,
                    stop_loss_price=9.2,
                    status="OPEN",
                )
            )
            _seed_price(db, hold_stock.id, run_date, close=10.0)
            _seed_price(db, buy_stock.id, run_date, close=10.0)
            db.add(
                Signal(
                    trade_date=run_date,
                    stock_id=buy_stock.id,
                    strategy_name="multi_factor_v1",
                    action="BUY",
                    score=0.95,
                    target_weight=0.5,
                    reason="Try to buy.",
                    status="NEW",
                )
            )
            db.commit()
        finally:
            db.close()

        run_resp = client.post(
            "/api/v1/simulation/run",
            json={
                "trade_date": "2024-04-30",
                "account_name": account_name,
            },
        )
        assert run_resp.status_code == 200
        assert run_resp.json()["rejected_count"] >= 1

        db = SessionLocal()
        try:
            rejected_buy = db.execute(
                select(Order).where(
                    and_(
                        Order.account_name == account_name,
                        Order.side == "BUY",
                        Order.status == "REJECTED",
                        Order.note.like("%Exposure limit reached%"),
                    )
                )
            ).scalar_one_or_none()
            assert rejected_buy is not None

            exposure_logs = db.execute(
                select(RiskLog).where(
                    and_(
                        RiskLog.account_name == account_name,
                        RiskLog.risk_type == "EXPOSURE_LIMIT",
                        RiskLog.resolved.is_(False),
                    )
                )
            ).scalars().all()
            assert len(exposure_logs) >= 1
        finally:
            db.close()

        risk_resp = client.get(f"/api/v1/risk?account_name={account_name}")
        assert risk_resp.status_code == 200
        assert any(item["risk_type"] == "EXPOSURE_LIMIT" for item in risk_resp.json()["alerts"])
    finally:
        get_settings.cache_clear()


def test_risk_endpoint_merges_unresolved_logs(client) -> None:
    """Risk API should include unresolved historical risk logs in alert list."""
    account_name = "risk_log_account"
    snapshot_date = date(2024, 4, 30)

    db = SessionLocal()
    try:
        db.add(
            Portfolio(
                account_name=account_name,
                as_of_date=snapshot_date,
                cash=800_000.0,
                market_value=200_000.0,
                total_asset=1_000_000.0,
                daily_pnl=0.0,
                cumulative_return=0.0,
                nav=1.0,
                position_ratio=0.2,
                max_drawdown=0.02,
            )
        )
        db.add(
            RiskLog(
                risk_date=date(2024, 4, 25),
                account_name=account_name,
                risk_type="MAX_DRAWDOWN",
                level="WARNING",
                message="Historical drawdown warning.",
                metric_value=0.12,
                threshold_value=0.1,
                resolved=False,
            )
        )
        db.commit()
    finally:
        db.close()

    risk_resp = client.get(f"/api/v1/risk?account_name={account_name}")
    assert risk_resp.status_code == 200

    payload = risk_resp.json()
    assert payload["overall_level"] == "WARNING"
    assert any(item["message"] == "Historical drawdown warning." for item in payload["alerts"])
