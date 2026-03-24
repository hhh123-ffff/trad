from datetime import date

import pandas as pd

from app.services.data.providers.base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    """Local mock provider used for offline development and tests."""

    def fetch_stock_list(self) -> pd.DataFrame:
        """Return deterministic sample stock universe."""
        return pd.DataFrame(
            [
                {"symbol": "000001.SZ", "name": "PingAnBank", "exchange": "SZSE", "industry": "Bank", "listing_date": "1991-04-03"},
                {"symbol": "600000.SH", "name": "SPDB", "exchange": "SSE", "industry": "Bank", "listing_date": "1999-11-10"},
                {"symbol": "600519.SH", "name": "KweichowMoutai", "exchange": "SSE", "industry": "Liquor", "listing_date": "2001-08-27"},
            ]
        )

    def fetch_daily_prices(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Generate deterministic mock OHLCV bars by date sequence."""
        trading_days = pd.date_range(start=start_date, end=end_date, freq="B")
        if trading_days.empty:
            return pd.DataFrame(columns=["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"])

        rows: list[dict] = []
        base = 10 + (sum(ord(ch) for ch in symbol) % 20)
        for index, trade_day in enumerate(trading_days):
            open_price = base + index * 0.2
            close_price = open_price + ((index % 5) - 2) * 0.1
            high_price = max(open_price, close_price) + 0.3
            low_price = min(open_price, close_price) - 0.3
            volume = 1_000_000 + index * 10_000
            amount = volume * close_price
            rows.append(
                {
                    "symbol": symbol,
                    "trade_date": trade_day.date(),
                    "open": round(open_price, 4),
                    "high": round(high_price, 4),
                    "low": round(low_price, 4),
                    "close": round(close_price, 4),
                    "volume": int(volume),
                    "amount": round(amount, 2),
                }
            )

        return pd.DataFrame(rows)
