from datetime import date

from app.core.logger import logger
from app.db.session import SessionLocal
from app.services.simulation.engine import PaperTradingEngine


def run_daily_paper_trading(run_date: date | None = None) -> dict:
    """Run daily paper trading simulation job and return summary payload."""
    db = SessionLocal()
    try:
        engine = PaperTradingEngine()
        result = engine.run(db=db, run_date=run_date, account_name=None)
        payload = {
            "account_name": result.account_name,
            "trade_date": result.trade_date.isoformat(),
            "orders_created": result.orders_created,
            "buy_count": result.buy_count,
            "sell_count": result.sell_count,
            "rejected_count": result.rejected_count,
            "cash": result.cash,
            "market_value": result.market_value,
            "total_asset": result.total_asset,
            "position_ratio": result.position_ratio,
        }
        logger.info("Daily paper trading job completed: {}", payload)
        return payload
    except Exception as exc:
        logger.exception("Daily paper trading job failed: {}", exc)
        raise
    finally:
        db.close()
