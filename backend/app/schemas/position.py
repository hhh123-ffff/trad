from datetime import date

from pydantic import BaseModel, Field


class PositionView(BaseModel):
    """Position item for positions page and API."""

    snapshot_date: date
    symbol: str
    name: str
    quantity: int = Field(ge=0)
    avg_cost: float
    last_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    weight: float = Field(ge=0, le=1)
    stop_loss_price: float | None = None
