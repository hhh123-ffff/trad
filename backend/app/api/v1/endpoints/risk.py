from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.risk import RiskStatus
from app.services.trading_service import get_risk_status

router = APIRouter()


@router.get("/risk", response_model=RiskStatus)
def get_risk(
    account_name: str | None = Query(default=None, description="Optional account name filter."),
    db: Session = Depends(get_db),
) -> RiskStatus:
    """Return current risk status and alerts."""
    return get_risk_status(db=db, account_name=account_name)
