from datetime import date

import pandas as pd

from app.services.data.cleaner import clean_price_dataframe, clean_stock_dataframe


def test_clean_stock_dataframe() -> None:
    """Validate stock cleaner keeps required columns and deduplicates symbols."""
    raw = pd.DataFrame(
        [
            {"symbol": "000001.sz", "name": "A", "exchange": "szse", "industry": "bank", "listing_date": "2020-01-01"},
            {"symbol": "000001.SZ", "name": "A2", "exchange": "SZSE", "industry": "bank", "listing_date": "2020-01-02"},
        ]
    )

    cleaned = clean_stock_dataframe(raw)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["symbol"] == "000001.SZ"
    assert cleaned.iloc[0]["name"] == "A2"


def test_clean_price_dataframe() -> None:
    """Validate price cleaner parses numeric/date fields and removes invalid rows."""
    raw = pd.DataFrame(
        [
            {"trade_date": "2024-01-02", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000, "amount": 10000},
            {"trade_date": "bad-date", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000, "amount": 10000},
        ]
    )

    cleaned = clean_price_dataframe(raw, symbol="000001.SZ")
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["symbol"] == "000001.SZ"
    assert cleaned.iloc[0]["trade_date"] == date(2024, 1, 2)
