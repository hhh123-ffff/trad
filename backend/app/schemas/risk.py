from pydantic import BaseModel


class RiskAlert(BaseModel):
    """Risk alert item for risk API."""

    level: str
    risk_type: str
    message: str


class RiskStatus(BaseModel):
    """Risk status payload for dashboard and alert center."""

    overall_level: str
    max_drawdown: float
    position_ratio: float
    alerts: list[RiskAlert]
