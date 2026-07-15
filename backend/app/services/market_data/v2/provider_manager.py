from __future__ import annotations

from collections.abc import Callable, Iterable

from app.core.config import get_settings
from app.services.market_data.v2.contracts import MarketDataProviderV2, MarketDataRequest, MarketDataUnavailable, NormalizedMarketData
from app.services.market_data.v2.providers.bcb import BancoCentralProviderV2
from app.services.market_data.v2.providers.brapi import BrapiMarketDataProviderV2
from app.services.market_data.v2.providers.coingecko import CoinGeckoProviderV2
from app.services.market_data.v2.providers.coinmarketcap import CoinMarketCapProviderV2
from app.services.market_data.v2.providers.dados_mercado import DadosMercadoProviderV2
from app.services.market_data.v2.providers.fmp import FinancialModelingPrepProviderV2
from app.services.market_data.v2.providers.fundamentus import FundamentusProviderV2
from app.services.market_data.v2.providers.mock import MockMarketDataProviderV2
from app.services.market_data.v2.providers.twelvedata import TwelveDataProviderV2
from app.services.market_data.v2.providers.yahoo import YahooFinanceChartProviderV2


class ProviderManager:
    def __init__(
        self,
        providers: Iterable[MarketDataProviderV2] | None = None,
        on_provider_error: Callable[[str, Exception], None] | None = None,
    ) -> None:
        if providers is None:
            providers = self._default_providers()
        self.providers = sorted(list(providers), key=lambda provider: provider.priority)
        self.on_provider_error = on_provider_error

    def _default_providers(self) -> list[MarketDataProviderV2]:
        settings = get_settings()
        configured = settings.market_data_provider.lower().strip()
        providers: list[MarketDataProviderV2] = []
        providers.append(BancoCentralProviderV2())
        providers.append(DadosMercadoProviderV2())
        if configured == "brapi" or settings.brapi_token:
            providers.append(BrapiMarketDataProviderV2())
        providers.append(CoinMarketCapProviderV2())
        providers.append(FinancialModelingPrepProviderV2())
        providers.append(TwelveDataProviderV2())
        providers.append(CoinGeckoProviderV2())
        providers.append(YahooFinanceChartProviderV2())
        if settings.fundamentus_enabled:
            providers.append(FundamentusProviderV2())
        providers.append(MockMarketDataProviderV2())
        return providers

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        errors: list[str] = []
        for provider in self.providers:
            if not provider.supports(data_type, request):
                continue
            try:
                data = provider.fetch(data_type, request)
                if errors:
                    return data.with_warning(f"fallback_after:{'|'.join(errors)}")
                return data
            except Exception as exc:
                if self.on_provider_error is not None:
                    self.on_provider_error(provider.name, exc)
                errors.append(f"{provider.name}:{exc.__class__.__name__}")
        message = f"Nenhum provider disponivel para {data_type}."
        if errors:
            message = f"{message} Falhas: {', '.join(errors)}"
        raise MarketDataUnavailable(message)
