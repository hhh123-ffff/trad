from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.signal import SignalView
from app.services.trading_service import list_signals

router = APIRouter()


@router.get("/signals", response_model=list[SignalView])
def get_signals(
    trade_date: date | None = Query(default=None, description="Filter by trade date (YYYY-MM-DD)."),
    strategy_name: str | None = Query(default=None, description="Filter by strategy name."),
    action: str | None = Query(default=None, description="Filter by signal action, e.g. BUY or SELL."),
    limit: int = Query(default=200, ge=1, le=500, description="Maximum number of items to return."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    db: Session = Depends(get_db),
) -> list[SignalView]:
    """Return strategy signals with optional filters and pagination."""
    return list_signals(
        db=db,
        trade_date=trade_date,
        strategy_name=strategy_name,
        action=action,
        limit=limit,
        offset=offset,
    )
