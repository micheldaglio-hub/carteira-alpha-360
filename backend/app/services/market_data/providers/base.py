from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Quote:
    ticker: str
    price: float
    currency: str = "BRL"


@dataclass(frozen=True)
class Fundamentals:
    ticker: str
    dividend_yield: float = 0
    payout: float = 0
    revenue_growth: float = 0
    profit_growth: float = 0
    net_margin: float = 0
    roe: float = 0
    roic: float = 0
    debt_to_ebitda: float = 0
    pe_ratio: float = 0
    pvp: float = 0


class MarketDataProvider(Protocol):
    name: str

    async def get_quote(self, ticker: str) -> Quote:
        ...

    async def get_fundamentals(self, ticker: str) -> Fundamentals:
        ...
