from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.market_data.v2.contracts import (
    DATA_TYPE_DIVIDENDS,
    DATA_TYPE_FUNDAMENTALS,
    DATA_TYPE_PRICE_HISTORY,
    DATA_TYPE_QUOTE,
    MarketDataProviderError,
    MarketDataRequest,
    NormalizedMarketData,
)
from app.services.market_data.v2.normalization import normalize_dividends, normalize_fundamentals, normalize_price_history, normalize_quote


class DadosMercadoProviderV2:
    """Optional Brazilian market-data provider.

    The adapter is intentionally conservative: it only becomes active when a
    token is present and all failures are treated as fallback events. Endpoint
    shapes can be refined when the paid account/docs are finalized.
    """

    name = "dados_mercado"
    priority = 18

    def __init__(self, timeout: float = 12.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout
        self.base_url = self.settings.dados_mercado_base_url.rstrip("/")

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        if not self.settings.dados_mercado_api_token:
            return False
        if (request.asset_class or "").lower() in {"cripto", "crypto"}:
            return False
        market = (request.market or "B3").upper()
        return market in {"", "B3", "BR", "BRASIL"} and data_type in {
            DATA_TYPE_QUOTE,
            DATA_TYPE_FUNDAMENTALS,
            DATA_TYPE_DIVIDENDS,
            DATA_TYPE_PRICE_HISTORY,
        }

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        symbol = request.normalized_symbol
        if data_type == DATA_TYPE_QUOTE:
            data = self._get_first((f"cotacoes/{symbol}", f"quotes/{symbol}", f"ativos/{symbol}/cotacao"))
            price = _pick(data, "preco", "price", "close", "valor")
            return normalize_quote(self.name, request, price=price, currency=request.currency or "BRL", raw=data)
        if data_type == DATA_TYPE_FUNDAMENTALS:
            data = self._get_first((f"fundamentos/{symbol}", f"ativos/{symbol}/fundamentos", f"indicadores/{symbol}"))
            raw = {
                "regularMarketPrice": _pick(data, "preco", "price"),
                "dividendYield": _pick(data, "dividend_yield", "dy", "dividendYield"),
                "payout": _pick(data, "payout"),
                "priceEarnings": _pick(data, "pl", "p_l", "pe_ratio"),
                "priceToBook": _pick(data, "pvp", "p_vp", "price_to_book"),
                "enterpriseToEbitda": _pick(data, "ev_ebitda", "evEbitda"),
                "returnOnEquity": _pick(data, "roe"),
                "roic": _pick(data, "roic"),
                "profitMargins": _pick(data, "margem_liquida", "net_margin"),
                "debtToEbitda": _pick(data, "divida_liquida_ebitda", "debt_to_ebitda"),
                "revenue": _pick(data, "receita", "revenue"),
                "profit": _pick(data, "lucro", "profit"),
                "marketCap": _pick(data, "valor_mercado", "market_value", "marketCap"),
            }
            return normalize_fundamentals(self.name, request, raw=raw, currency=request.currency or "BRL")
        if data_type == DATA_TYPE_DIVIDENDS:
            data = self._get_first((f"dividendos/{symbol}", f"ativos/{symbol}/dividendos"))
            rows = data if isinstance(data, list) else data.get("data") or data.get("dividendos") or []
            dividends = [
                {
                    "ex_date": row.get("data_com") or row.get("ex_date") or row.get("date"),
                    "payment_date": row.get("data_pagamento") or row.get("payment_date"),
                    "amount": _pick(row, "valor", "amount"),
                    "currency": request.currency or "BRL",
                    "source": self.name,
                }
                for row in rows
                if isinstance(row, dict)
            ]
            return normalize_dividends(self.name, request, dividends)
        if data_type == DATA_TYPE_PRICE_HISTORY:
            data = self._get_first((f"historico/{symbol}", f"ativos/{symbol}/historico"))
            rows = data if isinstance(data, list) else data.get("data") or data.get("prices") or []
            prices = [
                {
                    "date": row.get("data") or row.get("date"),
                    "close": _pick(row, "fechamento", "close"),
                    "open": row.get("abertura") or row.get("open"),
                    "high": row.get("maxima") or row.get("high"),
                    "low": row.get("minima") or row.get("low"),
                    "volume": row.get("volume"),
                    "currency": request.currency or "BRL",
                    "source": self.name,
                }
                for row in rows
                if isinstance(row, dict)
            ]
            return normalize_price_history(self.name, request, prices)
        raise MarketDataProviderError(f"Tipo de dado nao suportado pelo Dados de Mercado: {data_type}")

    def _get_first(self, paths: tuple[str, ...]):
        last_error: Exception | None = None
        for path in paths:
            try:
                data = self._get(path)
                if data not in (None, {}, []):
                    return data
            except Exception as exc:
                last_error = exc
        raise MarketDataProviderError("Dados de Mercado sem dados") from last_error

    def _get(self, path: str):
        headers = {"Authorization": f"Bearer {self.settings.dados_mercado_api_token}", "Accept": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/{path.lstrip('/')}", headers=headers)
            response.raise_for_status()
            return response.json()


def _pick(payload: dict, *keys: str):
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", 0, 0.0):
            return value
    return None
