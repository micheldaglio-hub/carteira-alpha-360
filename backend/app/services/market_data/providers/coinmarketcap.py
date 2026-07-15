from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class CryptoQuote:
    symbol: str
    price: float
    currency: str
    market_cap: float = 0
    percent_change_24h: float = 0


class CoinMarketCapProvider:
    name = "coinmarketcap"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_quote(self, symbol: str, convert: str = "BRL", timeout: float = 10.0) -> CryptoQuote | None:
        api_key = self.settings.coinmarketcap_api_key
        if not api_key:
            return None

        normalized = symbol.upper().strip()
        currency = convert.upper().strip() or "BRL"
        headers = {"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"}
        params = {"symbol": normalized, "convert": currency, "skip_invalid": "true"}
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(
                    "https://pro-api.coinmarketcap.com/v3/cryptocurrency/quotes/latest",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json().get("data", {})
        except Exception:
            return None

        row = None
        if isinstance(data, list):
            row = next((item for item in data if item.get("symbol") == normalized), data[0] if data else None)
        elif isinstance(data, dict):
            row = data.get(normalized)
        if isinstance(row, list):
            row = row[0] if row else None
        if not isinstance(row, dict):
            return None

        raw_quote = row.get("quote", {})
        if isinstance(raw_quote, list):
            quote = next(
                (
                    item
                    for item in raw_quote
                    if item.get("symbol") == currency or item.get("currency") == currency
                ),
                raw_quote[0] if raw_quote else {},
            )
        elif isinstance(raw_quote, dict):
            quote = raw_quote.get(currency, raw_quote)
        else:
            quote = {}
        price = float(quote.get("price") or 0)
        if price <= 0:
            return None
        return CryptoQuote(
            symbol=normalized,
            price=price,
            currency=currency,
            market_cap=float(quote.get("market_cap") or 0),
            percent_change_24h=float(quote.get("percent_change_24h") or 0),
        )
