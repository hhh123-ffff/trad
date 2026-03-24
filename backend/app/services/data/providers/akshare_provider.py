from datetime import date

import pandas as pd

from app.services.data.providers.base import MarketDataProvider


def _normalize_symbol(code: str) -> str:
    """Convert plain A-share code into unified symbol format."""
    code_str = str(code).strip()
    if code_str.endswith(".SH") or code_str.endswith(".SZ"):
        return code_str
    if code_str.startswith("6"):
        return f"{code_str}.SH"
    return f"{code_str}.SZ"


def _to_akshare_symbol(symbol: str) -> str:
    """Convert unified symbol to akshare raw symbol code."""
    return symbol.split(".")[0]


class AkshareMarketDataProvider(MarketDataProvider):
    """Akshare implementation for stock metadata and daily bars."""

    def __init__(self) -> None:
        """Initialize provider and validate dependency availability."""
        try:
            import akshare as ak  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("akshare is not installed.") from exc
        self.ak = ak

    def fetch_stock_list(self) -> pd.DataFrame:
        """Fetch stock universe using akshare code-name dataset."""
        try:
            raw_df = self.ak.stock_info_a_code_name()
        except Exception as exc:
            raise RuntimeError("Failed to fetch stock list from akshare.") from exc

        if raw_df.empty:
            return pd.DataFrame(columns=["symbol", "name", "exchange", "industry", "listing_date"])

        code_col = "code" if "code" in raw_df.columns else raw_df.columns[0]
        name_col = "name" if "name" in raw_df.columns else raw_df.columns[1]

        normalized = pd.DataFrame()
        normalized["symbol"] = raw_df[code_col].astype(str).map(_normalize_symbol)
        normalized["name"] = raw_df[name_col].astype(str)
        normalized["exchange"] = normalized["symbol"].str.endswith(".SH").map({True: "SSE", False: "SZSE"})
        normalized["industry"] = None
        normalized["listing_date"] = None
        return normalized

    def fetch_daily_prices(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch daily bars from akshare historical endpoint."""
        raw_symbol = _to_akshare_symbol(symbol)
        try:
            raw_df = self.ak.stock_zh_a_hist(
                symbol=raw_symbol,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="",
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch daily prices for {symbol} from akshare.") from exc

        if raw_df.empty:
            return pd.DataFrame(columns=["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"])

        mapping = {
            "日期": "trade_date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
        }
        missing = [column for column in mapping if column not in raw_df.columns]
        if missing:
            raise RuntimeError(f"Akshare daily data missing columns: {missing}")

        normalized = raw_df.rename(columns=mapping)
        normalized["symbol"] = _normalize_symbol(raw_symbol)
        return normalized[["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"]]
