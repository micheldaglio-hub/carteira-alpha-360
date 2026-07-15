from __future__ import annotations

from dataclasses import dataclass
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import MarketDataCacheEntry
from app.services.market_data.v2.cache import DatabaseMarketDataCache, InMemoryMarketDataCache
from app.services.market_data.v2.contracts import DATA_TYPE_QUOTE, MarketDataRequest, NormalizedMarketData
from app.services.market_data.v2.engine import MarketDataEngine
from app.services.market_data.v2.normalization import normalize_quote
from app.services.market_data.v2.provider_manager import ProviderManager
from app.services.market_data.v2.providers.bcb import BancoCentralProviderV2
from app.services.market_data.v2.providers.brapi import BrapiMarketDataProviderV2
from app.services.market_data.v2.providers.coingecko import CoinGeckoProviderV2
from app.services.market_data.v2.providers.fmp import FinancialModelingPrepProviderV2
from app.services.market_data.v2.providers.mock import MockMarketDataProviderV2


@dataclass
class CountingProvider:
    name: str = "counting"
    priority: int = 1
    calls: int = 0

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        return data_type == DATA_TYPE_QUOTE

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        self.calls += 1
        return normalize_quote(self.name, request, price=123.45, currency="BRL")


class FailingProvider:
    name = "failing"
    priority = 1

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        return True

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        raise RuntimeError("provider offline")


class MarketDataEngineV2Tests(unittest.TestCase):
    def test_mock_provider_returns_normalized_quote(self) -> None:
        engine = MarketDataEngine(provider_manager=ProviderManager([MockMarketDataProviderV2()]))

        quote = engine.get_quote("TAEE11", market="B3", asset_class="Acoes", currency="BRL")

        self.assertEqual(quote.data_type, DATA_TYPE_QUOTE)
        self.assertEqual(quote.provider, "mock")
        self.assertEqual(quote.source_symbol, "TAEE11")
        self.assertEqual(quote.currency, "BRL")
        self.assertGreater(quote.payload["price"], 0)

    def test_provider_manager_falls_back_to_mock_when_primary_fails(self) -> None:
        engine = MarketDataEngine(provider_manager=ProviderManager([FailingProvider(), MockMarketDataProviderV2()]))

        quote = engine.get_quote("WEGE3", market="B3", asset_class="Acoes", currency="BRL")

        self.assertEqual(quote.provider, "mock")
        self.assertTrue(any(item.startswith("fallback_after:") for item in quote.warnings))

    def test_in_memory_cache_avoids_second_provider_call(self) -> None:
        provider = CountingProvider()
        engine = MarketDataEngine(
            provider_manager=ProviderManager([provider]),
            cache=InMemoryMarketDataCache(),
        )

        first = engine.get_quote("ITSA4", market="B3", asset_class="Acoes", currency="BRL")
        second = engine.get_quote("ITSA4", market="B3", asset_class="Acoes", currency="BRL")

        self.assertEqual(provider.calls, 1)
        self.assertEqual(first.payload["price"], second.payload["price"])
        self.assertIn("cache_hit", second.warnings)

    def test_collect_fetches_multiple_providers_with_separate_cache(self) -> None:
        first_provider = CountingProvider(name="first")
        second_provider = CountingProvider(name="second")
        engine = MarketDataEngine(
            provider_manager=ProviderManager([first_provider, second_provider]),
            cache=InMemoryMarketDataCache(),
        )
        request = MarketDataRequest(symbol="ITSA4", market="B3", asset_class="Acoes", currency="BRL")

        first = engine.collect(DATA_TYPE_QUOTE, request)
        second = engine.collect(DATA_TYPE_QUOTE, request)

        self.assertEqual([item.provider for item in first], ["first", "second"])
        self.assertEqual([item.provider for item in second], ["first", "second"])
        self.assertEqual(first_provider.calls, 1)
        self.assertEqual(second_provider.calls, 1)

    def test_database_cache_persists_normalized_payload(self) -> None:
        db_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(db_engine)
        Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, expire_on_commit=False)
        db = Session()
        try:
            provider = CountingProvider()
            engine = MarketDataEngine(
                provider_manager=ProviderManager([provider]),
                cache=DatabaseMarketDataCache(db),
            )

            engine.get_quote("BOVA11", market="B3", asset_class="ETFs", currency="BRL")
            engine.get_quote("BOVA11", market="B3", asset_class="ETFs", currency="BRL")

            rows = db.execute(select(MarketDataCacheEntry)).scalars().all()
            self.assertEqual(provider.calls, 1)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].provider, "counting")
            self.assertEqual(rows[0].data_type, DATA_TYPE_QUOTE)
        finally:
            db.close()
            Base.metadata.drop_all(db_engine)
            db_engine.dispose()

    def test_brapi_v2_does_not_claim_crypto_support(self) -> None:
        provider = BrapiMarketDataProviderV2()

        supported = provider.supports(
            DATA_TYPE_QUOTE,
            MarketDataRequest(symbol="BTC", market="Crypto", asset_class="Cripto", currency="BRL"),
        )

        self.assertFalse(supported)

    def test_new_providers_advertise_scoped_support(self) -> None:
        fmp = FinancialModelingPrepProviderV2()
        fmp.settings.fmp_api_key = ""
        self.assertFalse(fmp.supports(DATA_TYPE_QUOTE, MarketDataRequest(symbol="AAPL", asset_class="Acoes")))

        coingecko = CoinGeckoProviderV2()
        self.assertTrue(coingecko.supports(DATA_TYPE_QUOTE, MarketDataRequest(symbol="BTC", market="Crypto", asset_class="Cripto")))
        self.assertFalse(coingecko.supports(DATA_TYPE_QUOTE, MarketDataRequest(symbol="AAPL", market="NASDAQ", asset_class="Acoes")))

        bcb = BancoCentralProviderV2()
        self.assertTrue(
            bcb.supports(
                "fx_rate",
                MarketDataRequest(symbol="USD", base_currency="USD", quote_currency="BRL", currency="BRL"),
            )
        )


if __name__ == "__main__":
    unittest.main()
