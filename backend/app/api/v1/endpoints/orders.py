from datetime import date

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.exceptions import ApiException
from app.db.session import get_db
from app.schemas.order import OrderView
from app.services.trading_service import get_order_by_id, list_orders

router = APIRouter()


@router.get("/orders", response_model=list[OrderView])
def get_orders(
    account_name: str | None = Query(default=None, description="Optional account name filter."),
    date_from: date | None = Query(default=None, description="Filter start date (YYYY-MM-DD)."),
    date_to: date | None = Query(default=None, description="Filter end date (YYYY-MM-DD)."),
    status: str | None = Query(default=None, description="Order status filter, e.g. FILLED."),
    side: str | None = Query(default=None, description="Order side filter, e.g. BUY or SELL."),
    symbol: str | None = Query(default=None, description="Filter by stock symbol."),
    limit: int = Query(default=200, ge=1, le=500, description="Maximum number of items to return."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    db: Session = Depends(get_db),
) -> list[OrderView]:
    """Return order history with optional filters and pagination."""
    return list_orders(
        db=db,
        account_name=account_name,
        date_from=date_from,
        date_to=date_to,
        status=status,
        side=side,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )


@router.get("/orders/{order_id}", response_model=OrderView)
def get_order(
    order_id: int = Path(..., ge=1, description="Order id."),
    db: Session = Depends(get_db),
) -> OrderView:
    """Return one order by id."""
    order = get_order_by_id(db=db, order_id=order_id)
    if order is None:
        raise ApiException(status_code=404, detail=f"Order {order_id} not found.")
    return order
