from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class MarketDataProvider(ABC):
    """Abstract data provider for stock universe and daily prices."""

    @abstractmethod
    def fetch_stock_list(self) -> pd.DataFrame:
        """Fetch stock universe metadata as a DataFrame."""

    @abstractmethod
    def fetch_daily_prices(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch symbol-level daily prices as a DataFrame."""
