from datetime import date

from pydantic import BaseModel, Field


class SignalView(BaseModel):
    """Signal item for strategy output API."""

    trade_date: date
    symbol: str
    strategy_name: str
    action: str
    score: float = 0.0
    target_weight: float = Field(default=0.0, ge=0, le=1)
    reason: str = ""
    status: str = "NEW"
    momentum_20: float | None = None
    momentum_60: float | None = None
    volume_factor: float | None = None
    volatility_20: float | None = None
    fundamental_factor: float | None = None
