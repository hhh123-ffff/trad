from app.core.config import get_settings
from app.services.data.providers.akshare_provider import AkshareMarketDataProvider
from app.services.data.providers.base import MarketDataProvider
from app.services.data.providers.mock_provider import MockMarketDataProvider
from app.services.data.providers.tushare_provider import TushareMarketDataProvider


def build_data_provider() -> MarketDataProvider:
    """Create data provider instance according to runtime settings."""
    settings = get_settings()

    if settings.data_provider == "mock":
        return MockMarketDataProvider()
    if settings.data_provider == "akshare":
        return AkshareMarketDataProvider()
    if settings.data_provider == "tushare":
        return TushareMarketDataProvider(token=settings.tushare_token)

    raise RuntimeError(f"Unsupported data provider: {settings.data_provider}")
