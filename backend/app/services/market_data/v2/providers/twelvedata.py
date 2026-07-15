from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.services.market_data.v2.contracts import (
    DATA_TYPE_ASSET_SEARCH,
    DATA_TYPE_DIVIDENDS,
    DATA_TYPE_FUNDAMENTALS,
    DATA_TYPE_PRICE_HISTORY,
    DATA_TYPE_QUOTE,
    MarketDataProviderError,
    MarketDataRequest,
    NormalizedMarketData,
)
from app.services.market_data.v2.normalization import (
    normalize_asset_search,
    normalize_dividends,
    normalize_fundamentals,
    normalize_price_history,
    normalize_quote,
)


class TwelveDataProviderV2:
    name = "twelvedata"
    priority = 45

    def __init__(self, timeout: float = 12.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout
        self.base_url = self.settings.twelve_data_base_url.rstrip("/")

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        if not self.settings.twelve_data_api_key:
            return False
        return data_type in {
            DATA_TYPE_QUOTE,
            DATA_TYPE_FUNDAMENTALS,
            DATA_TYPE_DIVIDENDS,
            DATA_TYPE_PRICE_HISTORY,
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
        if data_type == DATA_TYPE_ASSET_SEARCH:
            return self._search(request)
        raise MarketDataProviderError(f"Tipo de dado nao suportado pelo Twelve Data: {data_type}")

    def _quote(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = self._symbol(request)
        data = self._get("quote", {"symbol": symbol})
        price = _pick(data, "close", "price", "previous_close")
        currency = data.get("currency") or request.currency or "USD"
        return normalize_quote(self.name, request, price=price, currency=currency, providerSymbol=symbol, raw=data)

    def _fundamentals(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = self._symbol(request)
        stats = self._get_optional("statistics", {"symbol": symbol}) or {}
        profile = self._get_optional("profile", {"symbol": symbol}) or {}
        raw = {
            "regularMarketPrice": _pick(stats, "close", "price") or _pick(profile, "price"),
            "dividendYield": _pick(stats, "dividend_yield", "dividendYield", "yield"),
            "payoutRatio": _pick(stats, "payout_ratio", "payoutRatio"),
            "priceEarnings": _pick(stats, "pe_ratio", "trailing_pe", "pe"),
            "priceToBook": _pick(stats, "price_to_book", "pb_ratio"),
            "profitMargins": _pick(stats, "profit_margin", "net_margin"),
            "returnOnEquity": _pick(stats, "return_on_equity", "roe"),
            "marketCap": _pick(stats, "market_capitalization", "market_cap") or _pick(profile, "market_cap"),
        }
        return normalize_fundamentals(self.name, request, raw=raw, currency=request.currency or "USD").with_warning(f"provider_symbol:{symbol}")

    def _dividends(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = self._symbol(request)
        data = self._get("dividends", {"symbol": symbol})
        rows = data.get("dividends") or data.get("values") or []
        dividends = [
            {
                "ex_date": row.get("ex_date") or row.get("date"),
                "payment_date": row.get("payment_date") or row.get("paymentDate"),
                "amount": _pick(row, "amount", "cash_amount"),
                "currency": row.get("currency") or request.currency or "USD",
                "source": self.name,
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return normalize_dividends(self.name, request, dividends)

    def _price_history(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = self._symbol(request)
        params: dict[str, Any] = {"symbol": symbol, "interval": request.interval or "1day", "outputsize": 5000}
        if request.start_date:
            params["start_date"] = request.start_date.isoformat()
        if request.end_date:
            params["end_date"] = request.end_date.isoformat()
        data = self._get("time_series", params)
        rows = data.get("values") or []
        prices = [
            {
                "date": row.get("datetime") or row.get("date"),
                "close": _pick(row, "close"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "volume": row.get("volume"),
                "currency": request.currency or data.get("currency") or "USD",
                "source": self.name,
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return normalize_price_history(self.name, request, prices)

    def _search(self, request: MarketDataRequest) -> NormalizedMarketData:
        data = self._get("symbol_search", {"symbol": request.query or request.symbol})
        rows = data.get("data") or []
        results = [
            {
                "symbol": row.get("symbol"),
                "name": row.get("instrument_name"),
                "market": row.get("exchange"),
                "asset_class": row.get("instrument_type") or "",
                "currency": row.get("currency") or "",
                "source": self.name,
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return normalize_asset_search(self.name, request, results)

    def _symbol(self, request: MarketDataRequest) -> str:
        symbol = request.normalized_symbol
        market = (request.market or "").upper()
        if market in {"B3", "BR", "BRASIL"} and "." not in symbol:
            return f"{symbol}.SA"
        return symbol

    def _get(self, path: str, params: dict[str, Any]) -> dict:
        data = self._get_optional(path, params)
        if not isinstance(data, dict) or data.get("status") == "error":
            message = data.get("message") if isinstance(data, dict) else "sem resposta"
            raise MarketDataProviderError(f"Twelve Data sem dados em {path}: {message}")
        return data

    def _get_optional(self, path: str, params: dict[str, Any]) -> dict | None:
        request_params = {**params, "apikey": self.settings.twelve_data_api_key}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/{path.lstrip('/')}", params=request_params)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None
        return data if isinstance(data, dict) else None


def _pick(payload: dict, *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", 0, 0.0):
            return value
    return None
