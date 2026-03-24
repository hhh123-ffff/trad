from datetime import date

import pandas as pd

from app.services.data.providers.base import MarketDataProvider


def _normalize_ts_code(ts_code: str) -> str:
    """Convert tushare ts_code format to unified symbol format."""
    code = str(ts_code).strip().upper()
    if "." in code:
        left, right = code.split(".")
        return f"{left}.{right}"
    if code.startswith("6"):
        return f"{code}.SH"
    return f"{code}.SZ"


def _to_ts_code(symbol: str) -> str:
    """Convert unified symbol format to tushare ts_code format."""
    if "." in symbol:
        left, right = symbol.split(".")
        return f"{left}.{right}"
    if symbol.startswith("6"):
        return f"{symbol}.SH"
    return f"{symbol}.SZ"


class TushareMarketDataProvider(MarketDataProvider):
    """Tushare implementation for stock metadata and daily bars."""

    def __init__(self, token: str) -> None:
        """Initialize provider and validate token and dependency availability."""
        if not token.strip():
            raise RuntimeError("TUSHARE_TOKEN is required when using tushare provider.")

        try:
            import tushare as ts  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("tushare is not installed.") from exc

        ts.set_token(token)
        self.pro = ts.pro_api()

    def fetch_stock_list(self) -> pd.DataFrame:
        """Fetch stock universe from tushare stock_basic endpoint."""
        try:
            raw_df = self.pro.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,area,industry,list_date")
        except Exception as exc:
            raise RuntimeError("Failed to fetch stock list from tushare.") from exc

        if raw_df.empty:
            return pd.DataFrame(columns=["symbol", "name", "exchange", "industry", "listing_date"])

        normalized = pd.DataFrame()
        normalized["symbol"] = raw_df["ts_code"].astype(str).map(_normalize_ts_code)
        normalized["name"] = raw_df["name"].astype(str)
        normalized["exchange"] = raw_df["ts_code"].astype(str).str.endswith(".SH").map({True: "SSE", False: "SZSE"})
        normalized["industry"] = raw_df["industry"].astype(str)
        normalized["listing_date"] = pd.to_datetime(raw_df["list_date"], format="%Y%m%d", errors="coerce").dt.date
        return normalized

    def fetch_daily_prices(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch daily bars from tushare daily endpoint."""
        ts_code = _to_ts_code(symbol)
        try:
            raw_df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch daily prices for {symbol} from tushare.") from exc

        if raw_df.empty:
            return pd.DataFrame(columns=["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"])

        normalized = pd.DataFrame()
        normalized["symbol"] = raw_df["ts_code"].astype(str).map(_normalize_ts_code)
        normalized["trade_date"] = pd.to_datetime(raw_df["trade_date"], format="%Y%m%d", errors="coerce").dt.date
        normalized["open"] = raw_df["open"]
        normalized["high"] = raw_df["high"]
        normalized["low"] = raw_df["low"]
        normalized["close"] = raw_df["close"]
        normalized["volume"] = raw_df["vol"]
        normalized["amount"] = raw_df["amount"]
        return normalized
