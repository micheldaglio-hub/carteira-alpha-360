from __future__ import annotations

from app.services.market_data.providers.base import Fundamentals, Quote


MOCK_QUOTES = {
    "PETR4": 38.42,
    "ITSA4": 10.72,
    "TAEE11": 35.16,
    "HGLG11": 164.8,
    "KNRI11": 158.9,
    "BOVA11": 128.4,
    "IVVB11": 325.2,
    "WEGE3": 41.9,
    "RENT3": 47.7,
}


class MockMarketDataProvider:
    name = "mock"

    async def get_quote(self, ticker: str) -> Quote:
        normalized = ticker.upper().strip()
        return Quote(ticker=normalized, price=MOCK_QUOTES.get(normalized, 25.0))

    async def get_fundamentals(self, ticker: str) -> Fundamentals:
        normalized = ticker.upper().strip()
        return Fundamentals(
            ticker=normalized,
            dividend_yield=7.2 if normalized.endswith("11") else 4.8,
            payout=68,
            revenue_growth=8.5,
            profit_growth=9.2,
            net_margin=18,
            roe=16,
            roic=13,
            debt_to_ebitda=1.8,
            pe_ratio=10.5,
            pvp=1.2,
        )
