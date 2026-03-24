from datetime import date, timedelta

from app.core.logger import logger
from app.db.session import SessionLocal
from app.services.strategy.factor_engine import FactorEngine
from app.services.strategy.strategy_engine import MultiFactorStrategyEngine


def run_weekly_strategy() -> dict:
    """Run factor update and weekly strategy signal generation job."""
    db = SessionLocal()
    try:
        today = date.today()
        factor_engine = FactorEngine()
        factor_result = factor_engine.run(
            db=db,
            start_date=today - timedelta(days=180),
            end_date=today,
            symbols=None,
            factor_version="v1",
        )

        strategy_engine = MultiFactorStrategyEngine(factor_engine=factor_engine)
        strategy_result = strategy_engine.run(
            db=db,
            trade_date=today,
            factor_version="v1",
            force_rebalance=False,
        )

        payload = {
            "factor_symbols": factor_result.symbols_processed,
            "factor_dates": factor_result.trade_dates,
            "signal_status": strategy_result.status,
            "buy_count": strategy_result.buy_count,
            "sell_count": strategy_result.sell_count,
            "hold_count": strategy_result.hold_count,
        }
        logger.info("Weekly strategy job completed: {}", payload)
        return payload
    except Exception as exc:
        logger.exception("Weekly strategy job failed: {}", exc)
        raise
    finally:
        db.close()
