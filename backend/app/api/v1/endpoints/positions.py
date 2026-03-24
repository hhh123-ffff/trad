from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.position import PositionView
from app.services.trading_service import list_positions

router = APIRouter()


@router.get("/positions", response_model=list[PositionView])
def get_positions(
    account_name: str | None = Query(default=None, description="Optional account name filter."),
    snapshot_date: date | None = Query(default=None, description="Filter by snapshot date (YYYY-MM-DD)."),
    symbol: str | None = Query(default=None, description="Filter by stock symbol."),
    limit: int = Query(default=200, ge=1, le=500, description="Maximum number of items to return."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    db: Session = Depends(get_db),
) -> list[PositionView]:
    """Return current account positions with optional filters and pagination."""
    return list_positions(
        db=db,
        account_name=account_name,
        snapshot_date=snapshot_date,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )
