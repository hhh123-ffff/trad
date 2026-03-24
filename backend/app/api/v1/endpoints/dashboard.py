from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardOverview
from app.services.trading_service import get_dashboard_overview

router = APIRouter()


@router.get("/dashboard", response_model=DashboardOverview)
def get_dashboard(
    account_name: str | None = Query(default=None, description="Optional account name filter."),
    days: int = Query(default=120, ge=1, le=1000, description="Number of NAV points to return."),
    db: Session = Depends(get_db),
) -> DashboardOverview:
    """Return dashboard overview payload with optional account filter."""
    return get_dashboard_overview(db=db, account_name=account_name, days=days)
