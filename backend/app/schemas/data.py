from datetime import date

from pydantic import BaseModel, Field


class DataSyncRequest(BaseModel):
    """Request payload for manual data synchronization endpoint."""

    symbols: list[str] = Field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    include_stock_universe: bool = True


class DataSyncResponse(BaseModel):
    """Response payload for manual data synchronization endpoint."""

    provider: str
    stock_count: int
    price_inserted: int
    price_updated: int
    symbols_processed: int
