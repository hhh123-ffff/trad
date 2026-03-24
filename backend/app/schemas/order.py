from datetime import date

from pydantic import BaseModel, Field


class OrderView(BaseModel):
    """Order item for trade records API."""

    order_id: int
    account_name: str
    order_date: date
    symbol: str
    side: str
    quantity: int = Field(ge=0)
    filled_quantity: int = Field(ge=0)
    price: float = Field(ge=0)
    fee: float = Field(ge=0)
    status: str
    note: str = ""
