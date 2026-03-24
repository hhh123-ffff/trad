from datetime import date

from app.core.logger import logger
from app.db.session import SessionLocal
from app.services.data.ingestion import MarketDataIngestionService


def run_daily_data_update(symbols: list[str] | None = None) -> dict:
    """Run daily data update job and return execution summary."""
    db = SessionLocal()
    try:
        service = MarketDataIngestionService()
        today = date.today()
        result = service.run_full_sync(
            db=db,
            symbols=symbols,
            start_date=today,
            end_date=today,
            include_stock_universe=True,
        )

        payload = {
            "provider": result.provider,
            "stock_count": result.stock_count,
            "price_inserted": result.price_inserted,
            "price_updated": result.price_updated,
            "symbols_processed": result.symbols_processed,
        }
        logger.info("Daily data update completed: {}", payload)
        return payload
    except Exception as exc:
        logger.exception("Daily data update failed: {}", exc)
        raise
    finally:
        db.close()
