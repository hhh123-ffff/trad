from datetime import date

from pydantic import BaseModel, Field


class NavPoint(BaseModel):
    """Single net asset value observation point."""

    trade_date: date
    nav: float


class DashboardOverview(BaseModel):
    """Dashboard summary payload."""

    total_asset: float = Field(default=0)
    cash: float = Field(default=0)
    market_value: float = Field(default=0)
    today_pnl: float = Field(default=0)
    cumulative_return: float = Field(default=0)
    position_ratio: float = Field(default=0)
    max_drawdown: float = Field(default=0)
    nav_series: list[NavPoint] = Field(default_factory=list)
    stock_universe_size: int = Field(default=0)
