from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.market_data.providers.base import Fundamentals, Quote


class BrapiMarketDataProvider:
    name = "brapi"

    def __init__(self) -> None:
        self.settings = get_settings()

    async def get_quote(self, ticker: str) -> Quote:
        params = {}
        if self.settings.brapi_token:
            params["token"] = self.settings.brapi_token
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(f"https://brapi.dev/api/quote/{ticker.upper()}", params=params)
            response.raise_for_status()
            data = response.json().get("results", [{}])[0]
            return Quote(
                ticker=ticker.upper(),
                price=float(data.get("regularMarketPrice") or 0),
                currency=data.get("currency") or "BRL",
            )

    async def get_fundamentals(self, ticker: str) -> Fundamentals:
        params = {"fundamental": "true"}
        if self.settings.brapi_token:
            params["token"] = self.settings.brapi_token
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(f"https://brapi.dev/api/quote/{ticker.upper()}", params=params)
            response.raise_for_status()
            data = response.json().get("results", [{}])[0]
            return Fundamentals(
                ticker=ticker.upper(),
                dividend_yield=float(data.get("dividendYield") or 0),
                payout=float(data.get("payoutRatio") or 0),
                pe_ratio=float(data.get("priceEarnings") or 0),
                pvp=float(data.get("priceToBook") or 0),
            )
