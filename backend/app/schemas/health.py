from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health endpoint response model."""

    status: str = Field(default="ok")
    service: str
    env: str
    timestamp: datetime
