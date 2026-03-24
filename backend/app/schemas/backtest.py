from datetime import date, datetime

from pydantic import BaseModel, Field


class CurvePoint(BaseModel):
    """Single backtest curve observation point."""

    trade_date: date
    nav: float = Field(ge=0)
    drawdown: float
    daily_return: float = 0.0
    benchmark_nav: float | None = None


class BacktestOverview(BaseModel):
    """Backtest metrics and curve payload."""

    run_id: int | None = None
    strategy_name: str = ""
    benchmark_symbol: str = ""
    start_date: date | None = None
    end_date: date | None = None
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_return: float = 0.0
    status: str = "EMPTY"
    curve: list[CurvePoint]


class BacktestRunRequest(BaseModel):
    """Request payload for running historical backtest."""

    start_date: date
    end_date: date
    top_n: int | None = Field(default=None, gt=0)
    strategy_name: str | None = None
    factor_version: str = "v1"
    initial_nav: float = Field(default=1.0, gt=0)
    force_rebalance: bool = False


class BacktestRunResponse(BacktestOverview):
    """Response payload for historical backtest execution."""


class BacktestRunItem(BaseModel):
    """Compact item for backtest run listing endpoint."""

    run_id: int
    strategy_name: str
    benchmark_symbol: str
    start_date: date
    end_date: date
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_return: float
    status: str
    created_at: datetime


class BacktestRunListResponse(BaseModel):
    """Paginated backtest run list response payload."""

    total: int
    limit: int
    offset: int
    items: list[BacktestRunItem]
