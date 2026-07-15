from __future__ import annotations

from sqlalchemy.orm import Session

from app.engines.knowledge_engine import KnowledgeEngine
from app.models import MarketDataProviderEvent
from app.services.market_data.v2.cache import DatabaseMarketDataCache, InMemoryMarketDataCache
from app.services.market_data.v2.contracts import (
    DATA_TYPE_ASSET_SEARCH,
    DATA_TYPE_DIVIDENDS,
    DATA_TYPE_FUNDAMENTALS,
    DATA_TYPE_FX_RATE,
    DATA_TYPE_PRICE_HISTORY,
    DATA_TYPE_QUOTE,
    MarketDataRequest,
    MarketDataUnavailable,
    NormalizedMarketData,
)
from app.services.market_data.v2.provider_manager import ProviderManager


DEFAULT_TTLS = {
    DATA_TYPE_QUOTE: 60,
    DATA_TYPE_FUNDAMENTALS: 60 * 60 * 12,
    DATA_TYPE_DIVIDENDS: 60 * 60 * 24,
    DATA_TYPE_PRICE_HISTORY: 60 * 60 * 6,
    DATA_TYPE_FX_RATE: 60 * 15,
    DATA_TYPE_ASSET_SEARCH: 60 * 60,
}


class MarketDataEngine:
    def __init__(
        self,
        *,
        db: Session | None = None,
        provider_manager: ProviderManager | None = None,
        cache: InMemoryMarketDataCache | DatabaseMarketDataCache | None = None,
    ) -> None:
        self.db = db
        self.provider_manager = provider_manager or ProviderManager(on_provider_error=self._record_provider_error)
        self.cache = cache or (DatabaseMarketDataCache(db) if db is not None else InMemoryMarketDataCache())

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        cache_key = self._cache_key(data_type, request)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = self.provider_manager.fetch(data_type, request)
        except MarketDataUnavailable:
            stale = self.cache.get_any(cache_key)
            if stale is not None:
                return stale.with_warning("provider_unavailable")
            raise

        self.cache.set(cache_key, data, DEFAULT_TTLS.get(data_type, 300))
        self._persist_knowledge(data)
        return data

    def collect(
        self,
        data_type: str,
        request: MarketDataRequest,
        *,
        include_mock: bool = False,
    ) -> list[NormalizedMarketData]:
        """Fetch the same request from every available provider.

        This is used by validation engines that need evidence from multiple
        sources before declaring data insufficient. Each provider gets its own
        cache key so BRAPI, FMP, Twelve Data, Fundamentus and future providers
        can coexist without overwriting each other.
        """

        records: list[NormalizedMarketData] = []
        for provider in self.provider_manager.providers:
            if provider.name == "mock" and not include_mock:
                continue
            if not provider.supports(data_type, request):
                continue

            cache_key = self._cache_key(data_type, request, provider=provider.name)
            cached = self.cache.get(cache_key)
            if cached is not None:
                records.append(cached)
                continue

            try:
                data = provider.fetch(data_type, request)
            except Exception as exc:
                self._record_provider_error(provider.name, exc)
                stale = self.cache.get_any(cache_key)
                if stale is not None:
                    records.append(stale.with_warning("provider_unavailable"))
                continue

            self.cache.set(cache_key, data, DEFAULT_TTLS.get(data_type, 300))
            self._persist_knowledge(data)
            records.append(data)

        return records

    def get_quote(self, symbol: str, **kwargs) -> NormalizedMarketData:
        return self.fetch(DATA_TYPE_QUOTE, MarketDataRequest(symbol=symbol, **kwargs))

    def get_fundamentals(self, symbol: str, **kwargs) -> NormalizedMarketData:
        return self.fetch(DATA_TYPE_FUNDAMENTALS, MarketDataRequest(symbol=symbol, **kwargs))

    def get_dividends(self, symbol: str, **kwargs) -> NormalizedMarketData:
        return self.fetch(DATA_TYPE_DIVIDENDS, MarketDataRequest(symbol=symbol, **kwargs))

    def get_price_history(self, symbol: str, **kwargs) -> NormalizedMarketData:
        return self.fetch(DATA_TYPE_PRICE_HISTORY, MarketDataRequest(symbol=symbol, **kwargs))

    def get_fx_rate(self, base_currency: str, quote_currency: str, **kwargs) -> NormalizedMarketData:
        return self.fetch(
            DATA_TYPE_FX_RATE,
            MarketDataRequest(symbol=base_currency, base_currency=base_currency, quote_currency=quote_currency, **kwargs),
        )

    def search_assets(self, query: str, **kwargs) -> NormalizedMarketData:
        return self.fetch(DATA_TYPE_ASSET_SEARCH, MarketDataRequest(query=query, **kwargs))

    def _cache_key(self, data_type: str, request: MarketDataRequest, *, provider: str = "") -> str:
        start = request.start_date.isoformat() if request.start_date else ""
        end = request.end_date.isoformat() if request.end_date else ""
        parts = [
            "mde-v2",
            provider.lower(),
            data_type,
            request.normalized_symbol,
            request.market.upper(),
            request.asset_class.lower(),
            request.currency.upper(),
            request.base_currency.upper(),
            request.quote_currency.upper(),
            request.interval,
            start,
            end,
        ]
        return ":".join(parts)

    def _record_provider_error(self, provider: str, exc: Exception) -> None:
        if self.db is None:
            return
        event_type = exc.__class__.__name__
        severity = "warning"
        if event_type in {"MarketDataProviderBlocked", "MarketDataProviderTimeout"}:
            severity = "error"
        message = str(exc)[:2000]
        status_code = str(getattr(exc, "status_code", "") or "")
        try:
            self.db.add(
                MarketDataProviderEvent(
                    provider=provider,
                    event_type=event_type,
                    severity=severity,
                    message=message,
                    status_code=status_code,
                )
            )
            self.db.flush()
        except Exception:
            # Provider telemetry is useful, but it must never break a market data fallback chain.
            try:
                self.db.rollback()
            except Exception:
                pass

    def _persist_knowledge(self, data: NormalizedMarketData) -> None:
        if self.db is None or not data.asset_id:
            return
        KnowledgeEngine().save_market_data(self.db, data.asset_id, data)
