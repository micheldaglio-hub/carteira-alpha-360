from __future__ import annotations

from datetime import date, timedelta

from app.services.market_data.providers.mock import MOCK_QUOTES
from app.services.market_data.v2.contracts import (
    DATA_TYPE_ASSET_SEARCH,
    DATA_TYPE_DIVIDENDS,
    DATA_TYPE_FUNDAMENTALS,
    DATA_TYPE_FX_RATE,
    DATA_TYPE_PRICE_HISTORY,
    DATA_TYPE_QUOTE,
    MarketDataRequest,
    NormalizedMarketData,
)
from app.services.market_data.v2.normalization import (
    normalize_asset_search,
    normalize_dividends,
    normalize_fundamentals,
    normalize_fx_rate,
    normalize_price_history,
    normalize_quote,
)


class MockMarketDataProviderV2:
    name = "mock"
    priority = 1000

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        return data_type in {
            DATA_TYPE_QUOTE,
            DATA_TYPE_FUNDAMENTALS,
            DATA_TYPE_DIVIDENDS,
            DATA_TYPE_PRICE_HISTORY,
            DATA_TYPE_FX_RATE,
            DATA_TYPE_ASSET_SEARCH,
        }

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        if data_type == DATA_TYPE_QUOTE:
            return self._quote(request)
        if data_type == DATA_TYPE_FUNDAMENTALS:
            return self._fundamentals(request)
        if data_type == DATA_TYPE_DIVIDENDS:
            return self._dividends(request)
        if data_type == DATA_TYPE_PRICE_HISTORY:
            return self._price_history(request)
        if data_type == DATA_TYPE_FX_RATE:
            return self._fx_rate(request)
        if data_type == DATA_TYPE_ASSET_SEARCH:
            return self._search(request)
        raise ValueError(f"Tipo de dado nao suportado pelo mock: {data_type}")

    def _quote(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = request.normalized_symbol
        price = MOCK_QUOTES.get(symbol, 25.0)
        if (request.asset_class or "").lower() in {"cripto", "crypto"} and symbol in {"BTC", "ETH", "SOL"}:
            price = {"BTC": 350000.0, "ETH": 18500.0, "SOL": 820.0}[symbol]
        return normalize_quote(self.name, request, price=price, currency=request.currency or "BRL")

    def _fundamentals(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = request.normalized_symbol
        raw = {
            "regularMarketPrice": MOCK_QUOTES.get(symbol, 25.0),
            "dividendYield": 7.2 if symbol.endswith("11") else 4.8,
            "payoutRatio": 68,
            "revenueGrowth": 8.5,
            "earningsGrowth": 9.2,
            "profitMargins": 18,
            "returnOnEquity": 16,
            "roic": 13,
            "debtToEbitda": 1.8,
            "priceEarnings": 10.5,
            "priceToBook": 1.2,
        }
        if (request.asset_class or "").lower() in {"cripto", "crypto"}:
            raw.update({"dividendYield": 0, "payoutRatio": 0, "priceEarnings": 0, "priceToBook": 0})
        return normalize_fundamentals(self.name, request, raw=raw, currency=request.currency or "BRL")

    def _dividends(self, request: MarketDataRequest) -> NormalizedMarketData:
        today = date.today()
        dividends = [] if (request.asset_class or "").lower() in {"cripto", "crypto"} else [
            {"ex_date": str(today - timedelta(days=90)), "payment_date": str(today - timedelta(days=75)), "amount": 0.35, "currency": request.currency or "BRL"},
            {"ex_date": str(today - timedelta(days=180)), "payment_date": str(today - timedelta(days=165)), "amount": 0.32, "currency": request.currency or "BRL"},
        ]
        return normalize_dividends(self.name, request, dividends)

    def _price_history(self, request: MarketDataRequest) -> NormalizedMarketData:
        base = MOCK_QUOTES.get(request.normalized_symbol, 25.0)
        today = date.today()
        prices = [
            {
                "date": str(today - timedelta(days=days)),
                "close": round(base * (1 - days / 1200), 2),
                "currency": request.currency or "BRL",
            }
            for days in (90, 60, 30, 0)
        ]
        return normalize_price_history(self.name, request, prices)

    def _fx_rate(self, request: MarketDataRequest) -> NormalizedMarketData:
        base = (request.base_currency or request.symbol or "BRL").upper()
        quote = (request.quote_currency or request.currency or "BRL").upper()
        if base == quote:
            rate = 1
        elif base == "USD" and quote == "BRL":
            rate = 5.35
        elif base == "BRL" and quote == "USD":
            rate = 0.187
        else:
            rate = 1
        return normalize_fx_rate(self.name, request, rate=rate)

    def _search(self, request: MarketDataRequest) -> NormalizedMarketData:
        query = request.query.strip().upper()
        results = [
            {"symbol": symbol, "name": symbol, "market": "B3", "asset_class": "Acoes", "currency": "BRL"}
            for symbol in MOCK_QUOTES
            if not query or query in symbol
        ][:10]
        if query in {"BTC", "ETH", "SOL"}:
            results.insert(0, {"symbol": query, "name": query, "market": "Crypto", "asset_class": "Cripto", "currency": "BRL"})
        return normalize_asset_search(self.name, request, results)
