from __future__ import annotations

from datetime import datetime, time, timezone

import httpx

from app.services.market_data.v2.contracts import (
    DATA_TYPE_PRICE_HISTORY,
    MarketDataProviderError,
    MarketDataRequest,
    NormalizedMarketData,
)
from app.services.market_data.v2.normalization import normalize_price_history


class YahooFinanceChartProviderV2:
    name = "yahoo_finance"
    priority = 90

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        if data_type != DATA_TYPE_PRICE_HISTORY:
            return False
        return (request.asset_class or "").lower() not in {"cripto", "crypto"}

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        if data_type != DATA_TYPE_PRICE_HISTORY:
            raise MarketDataProviderError(f"Tipo de dado nao suportado pelo Yahoo Finance: {data_type}")
        return self._price_history(request)

    def _price_history(self, request: MarketDataRequest) -> NormalizedMarketData:
        errors = []
        for symbol in self._symbol_candidates(request):
            try:
                prices = self._fetch_symbol(symbol, request)
                if prices:
                    return normalize_price_history(self.name, request, prices).with_warning(f"provider_symbol:{symbol}")
            except Exception as exc:
                errors.append(f"{symbol}:{exc.__class__.__name__}")
        raise MarketDataProviderError(f"Yahoo Finance sem historico para {request.normalized_symbol}: {'|'.join(errors)}")

    def _fetch_symbol(self, symbol: str, request: MarketDataRequest) -> list[dict]:
        if request.start_date:
            start_dt = datetime.combine(request.start_date, time.min, tzinfo=timezone.utc)
        else:
            start_dt = datetime.now(timezone.utc).replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        if request.end_date:
            end_dt = datetime.combine(request.end_date, time.max, tzinfo=timezone.utc)
        else:
            end_dt = datetime.now(timezone.utc)
        params = {
            "period1": int(start_dt.timestamp()),
            "period2": int(end_dt.timestamp()),
            "interval": "1d",
            "includePrePost": "false",
            "events": "history",
        }
        with httpx.Client(timeout=self.timeout, headers={"User-Agent": "CarteiraAlpha360/0.1"}) as client:
            response = client.get(f"{self.base_url}/{symbol}", params=params)
            response.raise_for_status()
            payload = response.json()
        result = ((payload.get("chart") or {}).get("result") or [None])[0]
        if not isinstance(result, dict):
            return []
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators") or {}
        quote = (indicators.get("quote") or [{}])[0]
        adjclose = (indicators.get("adjclose") or [{}])[0].get("adjclose") or []
        closes = adjclose or quote.get("close") or []
        prices = []
        for index, raw_timestamp in enumerate(timestamps):
            if index >= len(closes) or closes[index] in (None, "", 0):
                continue
            day = datetime.fromtimestamp(int(raw_timestamp), tz=timezone.utc).date().isoformat()
            prices.append(
                {
                    "date": day,
                    "close": closes[index],
                    "open": _pick_list(quote.get("open") or [], index),
                    "high": _pick_list(quote.get("high") or [], index),
                    "low": _pick_list(quote.get("low") or [], index),
                    "volume": _pick_list(quote.get("volume") or [], index),
                    "currency": request.currency or "BRL",
                    "source": self.name,
                }
            )
        return prices

    def _symbol_candidates(self, request: MarketDataRequest) -> list[str]:
        symbol = request.normalized_symbol
        market = (request.market or "").upper()
        candidates = [symbol]
        if market in {"", "B3", "BR", "BRASIL"} and "." not in symbol:
            candidates.insert(0, f"{symbol}.SA")
        return list(dict.fromkeys(candidates))


def _pick_list(values: list, index: int):
    return values[index] if index < len(values) else None
