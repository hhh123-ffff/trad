from datetime import date

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.price import Price
from app.models.stock import Stock


def upsert_stocks(db: Session, stocks_df: pd.DataFrame) -> dict[str, int]:
    """Insert or update stock master data and return symbol-id mapping."""
    if stocks_df.empty:
        return {}

    symbols = stocks_df["symbol"].astype(str).tolist()
    existing_rows = db.execute(select(Stock).where(Stock.symbol.in_(symbols))).scalars().all()
    existing_map = {row.symbol: row for row in existing_rows}

    for row in stocks_df.to_dict(orient="records"):
        stock = existing_map.get(row["symbol"])
        if stock is None:
            stock = Stock(
                symbol=row["symbol"],
                name=row["name"],
                exchange=row["exchange"],
                industry=row.get("industry"),
                listing_date=row.get("listing_date"),
                status="ACTIVE",
            )
            db.add(stock)
        else:
            stock.name = row["name"]
            stock.exchange = row["exchange"]
            stock.industry = row.get("industry")
            stock.listing_date = row.get("listing_date")
            stock.status = "ACTIVE"

    db.flush()
    return get_symbol_to_id_map(db)


def get_symbol_to_id_map(db: Session) -> dict[str, int]:
    """Build symbol to stock id mapping from stock table."""
    rows = db.execute(select(Stock.symbol, Stock.id).where(Stock.status == "ACTIVE")).all()
    return {row[0]: row[1] for row in rows}


def upsert_prices(db: Session, prices_df: pd.DataFrame, symbol_to_id: dict[str, int]) -> tuple[int, int]:
    """Insert or update daily prices and return inserted/updated counts."""
    if prices_df.empty:
        return (0, 0)

    inserted = 0
    updated = 0

    for row in prices_df.to_dict(orient="records"):
        symbol = row["symbol"]
        stock_id = symbol_to_id.get(symbol)
        if stock_id is None:
            continue

        existing = db.execute(
            select(Price).where(and_(Price.stock_id == stock_id, Price.trade_date == row["trade_date"]))
        ).scalar_one_or_none()

        if existing is None:
            db.add(
                Price(
                    stock_id=stock_id,
                    trade_date=row["trade_date"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                    amount=float(row.get("amount", 0.0) or 0.0),
                )
            )
            inserted += 1
        else:
            existing.open = float(row["open"])
            existing.high = float(row["high"])
            existing.low = float(row["low"])
            existing.close = float(row["close"])
            existing.volume = int(row["volume"])
            existing.amount = float(row.get("amount", 0.0) or 0.0)
            updated += 1

    return (inserted, updated)


def get_all_symbols(db: Session) -> list[str]:
    """Return all active symbols from stock universe table."""
    rows = db.execute(select(Stock.symbol).where(Stock.status == "ACTIVE")).all()
    return [row[0] for row in rows]


def latest_trade_date(db: Session, stock_id: int) -> date | None:
    """Return latest trade date for a single stock."""
    row = db.execute(select(Price.trade_date).where(Price.stock_id == stock_id).order_by(Price.trade_date.desc())).first()
    return row[0] if row else None
