from __future__ import annotations

from app.core.config import get_settings
from app.services.market_data.providers.brapi import BrapiMarketDataProvider
from app.services.market_data.providers.mock import MockMarketDataProvider


def get_market_data_provider():
    provider = get_settings().market_data_provider.lower()
    if provider == "brapi":
        return BrapiMarketDataProvider()
    return MockMarketDataProvider()
