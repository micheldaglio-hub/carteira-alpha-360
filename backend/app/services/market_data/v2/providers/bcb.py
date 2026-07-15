from __future__ import annotations

from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.services.market_data.v2.contracts import (
    DATA_TYPE_FX_RATE,
    MarketDataProviderError,
    MarketDataRequest,
    NormalizedMarketData,
)
from app.services.market_data.v2.normalization import normalize_fx_rate


BCB_SGS_FX_CODES = {
    ("USD", "BRL"): "10813",
    ("EUR", "BRL"): "21619",
}


class BancoCentralProviderV2:
    name = "bcb"
    priority = 12

    def __init__(self, timeout: float = 10.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout
        self.base_url = self.settings.bcb_sgs_base_url.rstrip("/")

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        if data_type != DATA_TYPE_FX_RATE:
            return False
        base = (request.base_currency or request.symbol).upper()
        quote = (request.quote_currency or request.currency or "BRL").upper()
        return base == quote or (base, quote) in BCB_SGS_FX_CODES or (quote, base) in BCB_SGS_FX_CODES

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        if data_type != DATA_TYPE_FX_RATE:
            raise MarketDataProviderError(f"Tipo de dado nao suportado pelo Banco Central: {data_type}")
        base = (request.base_currency or request.symbol).upper()
        quote = (request.quote_currency or request.currency or "BRL").upper()
        if base == quote:
            return normalize_fx_rate(self.name, request, rate=1)

        invert = False
        code = BCB_SGS_FX_CODES.get((base, quote))
        if code is None:
            code = BCB_SGS_FX_CODES.get((quote, base))
            invert = True
        if code is None:
            raise MarketDataProviderError(f"Par de cambio nao suportado pelo Banco Central: {base}/{quote}")

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/bcdata.sgs.{code}/dados/ultimos/1", params={"formato": "json"})
                response.raise_for_status()
                rows = response.json()
        except Exception as exc:
            raise MarketDataProviderError("Banco Central SGS indisponivel") from exc
        if not rows:
            raise MarketDataProviderError("Banco Central SGS sem dados")

        rate = Decimal(str(rows[0].get("valor", "0")).replace(",", "."))
        if invert and rate:
            rate = Decimal("1") / rate
        return normalize_fx_rate(self.name, request, rate=float(rate))
