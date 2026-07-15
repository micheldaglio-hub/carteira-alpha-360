from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.market_data.v2.contracts import (
    DATA_TYPE_ASSET_SEARCH,
    DATA_TYPE_QUOTE,
    MarketDataProviderError,
    MarketDataRequest,
    NormalizedMarketData,
)
from app.services.market_data.v2.normalization import normalize_asset_search, normalize_quote


class CoinMarketCapProviderV2:
    name = "coinmarketcap"
    priority = 20

    def __init__(self, timeout: float = 12.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        if not self.settings.coinmarketcap_api_key:
            return False
        if (request.asset_class or "").lower() not in {"cripto", "crypto"} and (request.market or "").lower() != "crypto":
            return False
        return data_type in {DATA_TYPE_QUOTE, DATA_TYPE_ASSET_SEARCH}

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        if data_type == DATA_TYPE_QUOTE:
            return self._quote(request)
        if data_type == DATA_TYPE_ASSET_SEARCH:
            return self._search(request)
        raise MarketDataProviderError(f"Tipo de dado nao suportado pelo CoinMarketCap: {data_type}")

    def _quote(self, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = request.normalized_symbol
        currency = (request.currency or "BRL").upper()
        data = self._get(
            "https://pro-api.coinmarketcap.com/v3/cryptocurrency/quotes/latest",
            {"symbol": symbol, "convert": currency, "skip_invalid": "true"},
        )
        row = _extract_symbol_row(data.get("data"), symbol)
        quote = _extract_quote(row.get("quote"), currency)
        price = quote.get("price")
        if not price:
            raise MarketDataProviderError(f"CoinMarketCap sem preco para {symbol}")
        return normalize_quote(
            self.name,
            request,
            price=price,
            currency=currency,
            marketCap=quote.get("market_cap"),
            percentChange24h=quote.get("percent_change_24h"),
            raw=row,
        )

    def _search(self, request: MarketDataRequest) -> NormalizedMarketData:
        query = (request.query or request.symbol).strip()
        data = self._get(
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map",
            {"symbol": query.upper(), "limit": 10},
        )
        rows = data.get("data") or []
        results = [
            {
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "market": "Crypto",
                "asset_class": "Cripto",
                "currency": row.get("symbol"),
                "source": self.name,
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return normalize_asset_search(self.name, request, results)

    def _get(self, url: str, params: dict) -> dict:
        headers = {"X-CMC_PRO_API_KEY": self.settings.coinmarketcap_api_key, "Accept": "application/json"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise MarketDataProviderError("CoinMarketCap indisponivel") from exc
        if not isinstance(data, dict):
            raise MarketDataProviderError("CoinMarketCap retornou payload invalido")
        return data


def _extract_symbol_row(data, symbol: str) -> dict:
    if isinstance(data, list):
        row = next((item for item in data if item.get("symbol") == symbol), data[0] if data else None)
    elif isinstance(data, dict):
        row = data.get(symbol)
    else:
        row = None
    if isinstance(row, list):
        row = row[0] if row else None
    return row if isinstance(row, dict) else {}


def _extract_quote(raw_quote, currency: str) -> dict:
    if isinstance(raw_quote, list):
        return next(
            (
                item
                for item in raw_quote
                if item.get("symbol") == currency or item.get("currency") == currency
            ),
            raw_quote[0] if raw_quote else {},
        )
    if isinstance(raw_quote, dict):
        quote = raw_quote.get(currency, raw_quote)
        return quote if isinstance(quote, dict) else {}
    return {}
