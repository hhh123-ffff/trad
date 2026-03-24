from datetime import date

import pandas as pd


def clean_stock_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Standardize and validate stock metadata DataFrame."""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["symbol", "name", "exchange", "industry", "listing_date"])

    required = {"symbol", "name", "exchange"}
    missing = required - set(raw_df.columns)
    if missing:
        raise ValueError(f"Stock data missing required columns: {sorted(missing)}")

    cleaned = raw_df.copy()
    cleaned["symbol"] = cleaned["symbol"].astype(str).str.strip().str.upper()
    cleaned["name"] = cleaned["name"].astype(str).str.strip()
    cleaned["exchange"] = cleaned["exchange"].astype(str).str.strip().str.upper()

    if "industry" not in cleaned.columns:
        cleaned["industry"] = None
    else:
        cleaned["industry"] = cleaned["industry"].astype(str).replace({"nan": None, "None": None})

    if "listing_date" not in cleaned.columns:
        cleaned["listing_date"] = None
    else:
        cleaned["listing_date"] = pd.to_datetime(cleaned["listing_date"], errors="coerce").dt.date

    cleaned = cleaned.dropna(subset=["symbol", "name", "exchange"])
    cleaned = cleaned.drop_duplicates(subset=["symbol"], keep="last")
    cleaned = cleaned[cleaned["symbol"].str.len() > 0]

    return cleaned[["symbol", "name", "exchange", "industry", "listing_date"]]


def clean_price_dataframe(raw_df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Standardize and validate daily price DataFrame for one symbol."""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"])

    required = {"trade_date", "open", "high", "low", "close", "volume"}
    missing = required - set(raw_df.columns)
    if missing:
        raise ValueError(f"Price data missing required columns: {sorted(missing)}")

    cleaned = raw_df.copy()
    cleaned["symbol"] = symbol
    cleaned["trade_date"] = pd.to_datetime(cleaned["trade_date"], errors="coerce").dt.date

    for column in ["open", "high", "low", "close", "volume"]:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    if "amount" in cleaned.columns:
        cleaned["amount"] = pd.to_numeric(cleaned["amount"], errors="coerce")
    else:
        cleaned["amount"] = 0.0

    cleaned = cleaned.dropna(subset=["trade_date", "open", "high", "low", "close", "volume"])
    cleaned = cleaned[(cleaned["open"] >= 0) & (cleaned["high"] >= 0) & (cleaned["low"] >= 0) & (cleaned["close"] >= 0)]
    cleaned = cleaned[cleaned["volume"] >= 0]

    cleaned = cleaned.drop_duplicates(subset=["trade_date"], keep="last")
    cleaned = cleaned.sort_values(by="trade_date")

    return cleaned[["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"]]


def parse_date(value: str | None, default: date) -> date:
    """Parse date string in ISO format with fallback default."""
    if value is None or value.strip() == "":
        return default
    return pd.to_datetime(value, errors="raise").date()
