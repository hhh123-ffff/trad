from datetime import date

from pydantic import BaseModel, Field


class FactorRunRequest(BaseModel):
    """Request payload for factor calculation endpoint."""

    start_date: date
    end_date: date
    symbols: list[str] = Field(default_factory=list)
    factor_version: str = "v1"


class FactorRunResponse(BaseModel):
    """Response payload for factor calculation endpoint."""

    symbols_processed: int
    trade_dates: int
    records_inserted: int
    records_updated: int


class StrategyRunRequest(BaseModel):
    """Request payload for strategy run endpoint."""

    trade_date: date | None = None
    top_n: int | None = Field(default=None, gt=0)
    strategy_name: str | None = None
    factor_version: str = "v1"
    force_rebalance: bool = False


class StrategyRunResponse(BaseModel):
    """Response payload for strategy run endpoint."""

    trade_date: date
    strategy_name: str
    status: str
    timing_passed: bool
    reason: str
    selected_count: int
    buy_count: int
    sell_count: int
    hold_count: int
