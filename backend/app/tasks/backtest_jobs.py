from datetime import date, timedelta

from app.core.logger import logger
from app.db.session import SessionLocal
from app.services.backtest.engine import BacktestEngine


def run_periodic_backtest(days: int = 365) -> dict:
    """Run rolling-window historical backtest and return summary payload."""
    db = SessionLocal()
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        engine = BacktestEngine()
        result = engine.run(
            db=db,
            start_date=start_date,
            end_date=end_date,
            top_n=None,
            strategy_name=None,
            factor_version="v1",
            initial_nav=1.0,
            force_rebalance=False,
        )
        payload = {
            "run_id": result.run_id,
            "annual_return": result.annual_return,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "win_rate": result.win_rate,
            "total_return": result.total_return,
        }
        logger.info("Periodic backtest job completed: {}", payload)
        return payload
    except Exception as exc:
        logger.exception("Periodic backtest job failed: {}", exc)
        raise
    finally:
        db.close()
