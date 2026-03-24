from datetime import date

from pydantic import BaseModel


class SimulationRunRequest(BaseModel):
    """Request payload for paper trading simulation execution."""

    trade_date: date | None = None
    account_name: str | None = None


class SimulationRunResponse(BaseModel):
    """Response payload for paper trading simulation execution."""

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
