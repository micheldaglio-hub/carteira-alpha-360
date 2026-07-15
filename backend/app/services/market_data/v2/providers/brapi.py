from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.market_data.v2.contracts import (
    DATA_TYPE_FUNDAMENTALS,
    DATA_TYPE_QUOTE,
    MarketDataRequest,
    NormalizedMarketData,
)
from app.services.market_data.v2.normalization import normalize_fundamentals, normalize_quote


class BrapiMarketDataProviderV2:
    name = "brapi"
    priority = 10

    def __init__(self, timeout: float = 12.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        if data_type not in {DATA_TYPE_QUOTE, DATA_TYPE_FUNDAMENTALS}:
            return False
        if (request.asset_class or "").lower() in {"cripto", "crypto"}:
            return False
        market = (request.market or "").upper()
        return market in {"", "B3", "BR"}

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        params: dict[str, str] = {}
        if data_type == DATA_TYPE_FUNDAMENTALS:
            params["fundamental"] = "true"
        if self.settings.brapi_token:
            params["token"] = self.settings.brapi_token

        symbol = request.normalized_symbol
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"https://brapi.dev/api/quote/{symbol}", params=params)
            response.raise_for_status()
            data = response.json().get("results", [{}])[0]

        currency = data.get("currency") or request.currency or "BRL"
        if data_type == DATA_TYPE_QUOTE:
            return normalize_quote(
                self.name,
                request,
                price=data.get("regularMarketPrice"),
                currency=currency,
                shortName=data.get("shortName") or "",
                longName=data.get("longName") or "",
            )
        return normalize_fundamentals(self.name, request, raw=data, currency=currency)
