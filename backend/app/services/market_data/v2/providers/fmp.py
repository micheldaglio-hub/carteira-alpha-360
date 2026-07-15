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


class FinancialModelingPrepProviderV2:
    name = "fmp"
    priority = 35

    def __init__(self, timeout: float = 12.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout
        self.base_url = self.settings.fmp_base_url.rstrip("/")

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        if not self.settings.fmp_api_key:
            return False
        if (request.asset_class or "").lower() in {"cripto", "crypto"}:
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
        raise MarketDataProviderError(f"Tipo de dado nao suportado pelo FMP: {data_type}")

    def _quote(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol, row = self._first_symbol_response("quote", request, required_keys=("price",))
        price = _pick(row, "price", "priceAvg50", "previousClose")
        currency = row.get("currency") or request.currency or "USD"
        return normalize_quote(self.name, request, price=price, currency=currency, providerSymbol=symbol, raw=row)

    def _fundamentals(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = self._resolve_symbol(request)
        quote = self._first(self._get("quote", {"symbol": symbol}), {})
        profile = self._first(self._get("profile", {"symbol": symbol}), {})
        ratios = self._first(self._get_optional("ratios-ttm", {"symbol": symbol}), {})
        metrics = self._first(self._get_optional("key-metrics-ttm", {"symbol": symbol}), {})
        growth = self._first(self._get_optional("financial-growth", {"symbol": symbol}), {})

        raw = {
            "regularMarketPrice": _pick(quote, "price", "previousClose") or _pick(profile, "price"),
            "dividendYield": _pick(ratios, "dividendYieldTTM", "dividendYielTTM", "dividendYield")
            or _pick(metrics, "dividendYieldTTM", "dividendYield"),
            "payoutRatio": _pick(ratios, "payoutRatioTTM", "payoutRatio") or _pick(metrics, "payoutRatioTTM", "payoutRatio"),
            "priceEarnings": _pick(ratios, "priceEarningsRatioTTM", "peRatioTTM", "peRatio") or _pick(metrics, "peRatioTTM", "peRatio"),
            "priceToBook": _pick(ratios, "priceToBookRatioTTM", "priceBookValueRatioTTM")
            or _pick(metrics, "pbRatioTTM", "priceToBookRatioTTM"),
            "enterpriseToEbitda": _pick(ratios, "enterpriseValueMultipleTTM", "evToEbitdaTTM")
            or _pick(metrics, "enterpriseValueOverEBITDATTM"),
            "revenueGrowth": _pick(growth, "revenueGrowth", "growthRevenue"),
            "earningsGrowth": _pick(growth, "netIncomeGrowth", "growthNetIncome"),
            "profitMargins": _pick(ratios, "netProfitMarginTTM", "netIncomeMarginTTM"),
            "returnOnEquity": _pick(ratios, "returnOnEquityTTM", "roeTTM"),
            "roic": _pick(ratios, "returnOnInvestedCapitalTTM", "returnOnCapitalEmployedTTM", "roicTTM"),
            "debtToEbitda": _pick(ratios, "netDebtToEBITDATTM", "debtToEbitdaTTM"),
            "marketCap": _pick(profile, "mktCap", "marketCap") or _pick(quote, "marketCap"),
            "revenue": _pick(metrics, "revenuePerShareTTM"),
            "profit": _pick(metrics, "netIncomePerShareTTM"),
        }
        currency = quote.get("currency") or profile.get("currency") or request.currency or "USD"
        return normalize_fundamentals(self.name, request, raw=raw, currency=currency).with_warning(f"provider_symbol:{symbol}")

    def _dividends(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = self._resolve_symbol(request)
        rows = self._as_list(self._get("dividends", {"symbol": symbol}))
        dividends = [
            {
                "ex_date": row.get("date") or row.get("exDividendDate") or row.get("recordDate"),
                "payment_date": row.get("paymentDate") or row.get("date"),
                "amount": _pick(row, "dividend", "adjDividend", "amount"),
                "currency": row.get("currency") or request.currency or "USD",
                "source": self.name,
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return normalize_dividends(self.name, request, dividends)

    def _price_history(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = self._resolve_symbol(request)
        params: dict[str, Any] = {"symbol": symbol}
        if request.start_date:
            params["from"] = request.start_date.isoformat()
        if request.end_date:
            params["to"] = request.end_date.isoformat()
        data = self._get("historical-price-eod/full", params)
        rows = self._as_list(data.get("historical") if isinstance(data, dict) else data)
        prices = [
            {
                "date": row.get("date"),
                "close": _pick(row, "adjClose", "close"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "volume": row.get("volume"),
                "currency": request.currency or "USD",
                "source": self.name,
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return normalize_price_history(self.name, request, prices)

    def _search(self, request: MarketDataRequest) -> NormalizedMarketData:
        query = request.query or request.symbol
        rows = self._as_list(self._get("search-symbol", {"query": query, "limit": 10}))
        results = [
            {
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "market": row.get("exchangeShortName") or row.get("exchange"),
                "asset_class": "Acoes",
                "currency": row.get("currency") or "",
                "source": self.name,
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return normalize_asset_search(self.name, request, results)

    def _resolve_symbol(self, request: MarketDataRequest) -> str:
        for symbol in self._symbol_candidates(request):
            data = self._get_optional("quote", {"symbol": symbol})
            if self._as_list(data):
                return symbol
        return self._symbol_candidates(request)[0]

    def _first_symbol_response(self, path: str, request: MarketDataRequest, *, required_keys: tuple[str, ...] = ()) -> tuple[str, dict]:
        for symbol in self._symbol_candidates(request):
            rows = self._as_list(self._get_optional(path, {"symbol": symbol}))
            for row in rows:
                if isinstance(row, dict) and (not required_keys or any(row.get(key) for key in required_keys)):
                    return symbol, row
        raise MarketDataProviderError(f"FMP nao retornou dados para {request.normalized_symbol}")

    def _symbol_candidates(self, request: MarketDataRequest) -> list[str]:
        symbol = request.normalized_symbol
        market = (request.market or "").upper()
        candidates = [symbol]
        if market in {"B3", "BR", "BRASIL"} and "." not in symbol:
            candidates.insert(0, f"{symbol}.SA")
        return list(dict.fromkeys(candidates))

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        data = self._get_optional(path, params)
        if data in (None, {}, []):
            raise MarketDataProviderError(f"FMP sem dados em {path}")
        return data

    def _get_optional(self, path: str, params: dict[str, Any]) -> Any:
        request_params = {**params, "apikey": self.settings.fmp_api_key}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/{path.lstrip('/')}", params=request_params)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None
        if isinstance(data, dict) and (data.get("Error Message") or data.get("error")):
            return None
        return data

    def _as_list(self, data: Any) -> list:
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []

    def _first(self, data: Any, default: dict) -> dict:
        rows = self._as_list(data)
        return rows[0] if rows and isinstance(rows[0], dict) else default


def _pick(payload: dict, *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", 0, 0.0):
            return value
    return None
