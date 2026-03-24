from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return service liveness status."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        env=settings.app_env,
        timestamp=datetime.now(tz=timezone.utc),
    )


@router.get("/ready", response_model=HealthResponse)
def readiness_check() -> HealthResponse:
    """Return service readiness status."""
    settings = get_settings()
    return HealthResponse(
        status="ready",
        service=settings.app_name,
        env=settings.app_env,
        timestamp=datetime.now(tz=timezone.utc),
    )
