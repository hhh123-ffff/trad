from dataclasses import dataclass
from datetime import date, timedelta

from app.core.logger import logger
from app.services.data.cleaner import clean_price_dataframe, clean_stock_dataframe
from app.services.data.providers.base import MarketDataProvider
from app.services.data.providers.factory import build_data_provider
from app.services.data.repository import get_all_symbols, get_symbol_to_id_map, upsert_prices, upsert_stocks


@dataclass
class DataSyncResult:
    """Summary result for one data synchronization run."""

    provider: str
    stock_count: int
    price_inserted: int
    price_updated: int
    symbols_processed: int


class MarketDataIngestionService:
    """Orchestrates data collection, cleaning, and persistence."""

    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        """Initialize service with an explicit provider or runtime factory."""
        self.provider = provider or build_data_provider()

    def sync_stock_universe(self, db) -> dict[str, int]:
        """Fetch stock universe and persist into stock master table."""
        try:
            raw_stocks = self.provider.fetch_stock_list()
            clean_stocks = clean_stock_dataframe(raw_stocks)
            symbol_to_id = upsert_stocks(db, clean_stocks)
            db.commit()
            return symbol_to_id
        except Exception as exc:
            db.rollback()
            logger.exception("Failed to sync stock universe: {}", exc)
            raise

    def sync_prices(
        self,
        db,
        symbols: list[str],
        start_date: date,
        end_date: date,
        symbol_to_id: dict[str, int],
    ) -> tuple[int, int]:
        """Fetch and persist daily prices for selected symbols."""
        total_inserted = 0
        total_updated = 0

        for symbol in symbols:
            try:
                raw_prices = self.provider.fetch_daily_prices(symbol=symbol, start_date=start_date, end_date=end_date)
                clean_prices = clean_price_dataframe(raw_prices, symbol=symbol)
                inserted, updated = upsert_prices(db, clean_prices, symbol_to_id)
                total_inserted += inserted
                total_updated += updated
            except Exception as exc:
                logger.exception("Failed to sync prices for {}: {}", symbol, exc)

        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.exception("Failed to commit price sync transaction: {}", exc)
            raise

        return (total_inserted, total_updated)

    def run_full_sync(
        self,
        db,
        symbols: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        include_stock_universe: bool = True,
    ) -> DataSyncResult:
        """Run full data synchronization workflow and return summary."""
        final_end = end_date or date.today()
        final_start = start_date or (final_end - timedelta(days=7))

        symbol_to_id: dict[str, int]
        if include_stock_universe:
            symbol_to_id = self.sync_stock_universe(db)
        else:
            symbol_to_id = get_symbol_to_id_map(db)

        if symbols is None or len(symbols) == 0:
            symbols = sorted(get_all_symbols(db))

        inserted, updated = self.sync_prices(
            db=db,
            symbols=symbols,
            start_date=final_start,
            end_date=final_end,
            symbol_to_id=symbol_to_id,
        )

        return DataSyncResult(
            provider=self.provider.__class__.__name__,
            stock_count=len(symbol_to_id),
            price_inserted=inserted,
            price_updated=updated,
            symbols_processed=len(symbols),
        )
