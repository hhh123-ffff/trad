from datetime import date

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.price import Price
from app.models.stock import Stock
from app.services.data.ingestion import MarketDataIngestionService
from app.services.data.providers.mock_provider import MockMarketDataProvider


def test_run_full_sync_with_mock_provider() -> None:
    """Validate full data sync inserts stock and price records."""
    db = SessionLocal()
    try:
        service = MarketDataIngestionService(provider=MockMarketDataProvider())
        result = service.run_full_sync(
            db=db,
            symbols=["000001.SZ", "600000.SH"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 8),
            include_stock_universe=True,
        )

        stock_count = db.execute(select(Stock)).scalars().all()
        price_count = db.execute(select(Price)).scalars().all()

        assert result.stock_count >= 3
        assert result.price_inserted > 0
        assert len(stock_count) >= 3
        assert len(price_count) > 0
    finally:
        db.close()
