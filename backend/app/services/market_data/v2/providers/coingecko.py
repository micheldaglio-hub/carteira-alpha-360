from __future__ import annotations

from datetime import datetime, time, timezone

import httpx

from app.core.config import get_settings
from app.services.market_data.v2.contracts import (
    DATA_TYPE_ASSET_SEARCH,
    DATA_TYPE_PRICE_HISTORY,
    DATA_TYPE_QUOTE,
    MarketDataProviderError,
    MarketDataRequest,
    NormalizedMarketData,
)
from app.services.market_data.v2.normalization import normalize_asset_search, normalize_price_history, normalize_quote


COINGECKO_SYMBOL_IDS = {
    "ADA": ("cardano",),
    "BNB": ("binancecoin",),
    "BTC": ("bitcoin",),
    "DOGE": ("dogecoin",),
    "ETH": ("ethereum",),
    "FET": ("fetch-ai", "artificial-superintelligence-alliance"),
    "FLR": ("flare-networks", "flare"),
    "JASMY": ("jasmycoin",),
    "SHIB": ("shiba-inu",),
    "SOL": ("solana",),
    "USDC": ("usd-coin",),
    "USDT": ("tether",),
    "VET": ("vechain",),
    "XRP": ("ripple",),
}


class CoinGeckoProviderV2:
    name = "coingecko"
    priority = 55

    def __init__(self, timeout: float = 12.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout
        self.base_url = self.settings.coingecko_base_url.rstrip("/")

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        if (request.asset_class or "").lower() not in {"cripto", "crypto"} and (request.market or "").lower() != "crypto":
            return False
        return data_type in {DATA_TYPE_QUOTE, DATA_TYPE_ASSET_SEARCH, DATA_TYPE_PRICE_HISTORY}

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        if data_type == DATA_TYPE_QUOTE:
            return self._quote(request)
        if data_type == DATA_TYPE_ASSET_SEARCH:
            return self._search(request)
        if data_type == DATA_TYPE_PRICE_HISTORY:
            return self._price_history(request)
        raise MarketDataProviderError(f"Tipo de dado nao suportado pelo CoinGecko: {data_type}")

    def _quote(self, request: MarketDataRequest) -> NormalizedMarketData:
        coin_ids = self._coin_ids(request)
        currency = (request.currency or "brl").lower()
        data = self._get(
            "simple/price",
            {
                "ids": ",".join(coin_ids),
                "vs_currencies": currency,
                "include_market_cap": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
            },
        )
        selected_coin_id = ""
        row = {}
        for coin_id in coin_ids:
            candidate = data.get(coin_id) or {}
            if candidate.get(currency):
                selected_coin_id = coin_id
                row = candidate
                break
        price = row.get(currency)
        if not price:
            raise MarketDataProviderError(f"CoinGecko sem preco para {request.normalized_symbol}")
        return normalize_quote(
            self.name,
            request,
            price=price,
            currency=currency.upper(),
            marketCap=row.get(f"{currency}_market_cap"),
            percentChange24h=row.get(f"{currency}_24h_change"),
            lastUpdatedAt=row.get("last_updated_at"),
            raw={**row, "provider_id": selected_coin_id},
        )

    def _search(self, request: MarketDataRequest) -> NormalizedMarketData:
        data = self._get("search", {"query": request.query or request.symbol})
        rows = data.get("coins") or []
        results = [
            {
                "symbol": row.get("symbol", "").upper(),
                "name": row.get("name"),
                "market": "Crypto",
                "asset_class": "Cripto",
                "currency": row.get("symbol", "").upper(),
                "source": self.name,
                "provider_id": row.get("id"),
            }
            for row in rows[:10]
            if isinstance(row, dict)
        ]
        return normalize_asset_search(self.name, request, results)

    def _price_history(self, request: MarketDataRequest) -> NormalizedMarketData:
        coin_id = self._coin_ids(request)[0]
        currency = (request.currency or "brl").lower()
        if request.start_date:
            start_dt = datetime.combine(request.start_date, time.min, tzinfo=timezone.utc)
        else:
            start_dt = datetime.now(timezone.utc).replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        if request.end_date:
            end_dt = datetime.combine(request.end_date, time.max, tzinfo=timezone.utc)
        else:
            end_dt = datetime.now(timezone.utc)
        data = self._get(
            f"coins/{coin_id}/market_chart/range",
            {
                "vs_currency": currency,
                "from": int(start_dt.timestamp()),
                "to": int(end_dt.timestamp()),
            },
        )
        rows = data.get("prices") or []
        prices = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 2:
                continue
            day = datetime.fromtimestamp(float(row[0]) / 1000, tz=timezone.utc).date().isoformat()
            prices.append({"date": day, "close": row[1], "currency": currency.upper(), "source": self.name})
        return normalize_price_history(self.name, request, prices).with_warning(f"provider_id:{coin_id}")

    def _coin_ids(self, request: MarketDataRequest) -> list[str]:
        symbol = request.normalized_symbol.lower()
        upper_symbol = request.normalized_symbol.upper()
        provider_symbol = (request.provider_symbol or "").strip().lower()
        if provider_symbol and provider_symbol != symbol and " " not in provider_symbol:
            if provider_symbol.upper() in COINGECKO_SYMBOL_IDS:
                return list(COINGECKO_SYMBOL_IDS[provider_symbol.upper()])
            return [provider_symbol]
        if upper_symbol in COINGECKO_SYMBOL_IDS:
            return list(COINGECKO_SYMBOL_IDS[upper_symbol])
        data = self._get("search", {"query": symbol})
        rows = data.get("coins") or []
        exact = [
            row
            for row in rows
            if isinstance(row, dict) and str(row.get("symbol", "")).lower() == symbol and row.get("id")
        ]
        selected_rows = exact or [row for row in rows if isinstance(row, dict) and row.get("id")]
        if not selected_rows:
            raise MarketDataProviderError(f"CoinGecko sem id para {symbol}")
        return [str(row["id"]) for row in selected_rows[:3]]

    def _get(self, path: str, params: dict) -> dict:
        headers = {"Accept": "application/json"}
        if self.settings.coingecko_api_key:
            headers["x-cg-demo-api-key"] = self.settings.coingecko_api_key
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/{path.lstrip('/')}", headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise MarketDataProviderError("CoinGecko indisponivel") from exc
        if not isinstance(data, dict):
            raise MarketDataProviderError("CoinGecko retornou payload invalido")
        return data
