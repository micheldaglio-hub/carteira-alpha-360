from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.engines.knowledge_engine import KnowledgeEngine
from app.models import Asset, AssetFact, AssetMetricDivergence, MarketDataProviderEvent
from app.services.market_data.v2.contracts import DATA_TYPE_QUOTE, MarketDataRequest, NormalizedMarketData
from app.services.market_data.v2.engine import MarketDataEngine
from app.services.market_data.v2.normalization import normalize_fundamentals, normalize_quote
from app.services.market_data.v2.provider_manager import ProviderManager
from app.services.market_data.v2.providers.fundamentus import FundamentusProviderV2, extract_fundamentus_indicators
from app.services.market_data.v2.providers.mock import MockMarketDataProviderV2


@dataclass
class FailingProvider:
    name: str = "failing"
    priority: int = 1

    def supports(self, data_type: str, request: MarketDataRequest) -> bool:
        return data_type == DATA_TYPE_QUOTE

    def fetch(self, data_type: str, request: MarketDataRequest) -> NormalizedMarketData:
        raise RuntimeError("blocked")


class FundamentusKnowledgeEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_fundamentus_html_parser_extracts_expected_indicators(self) -> None:
        html = """
        <table>
          <tr><td>P/L</td><td>10,50</td></tr>
          <tr><td>P/VP</td><td>1,23</td></tr>
          <tr><td>EV/EBITDA</td><td>7,80</td></tr>
          <tr><td>ROE</td><td>16,20%</td></tr>
          <tr><td>ROIC</td><td>12,10%</td></tr>
          <tr><td>Marg. Liquida</td><td>18,40%</td></tr>
          <tr><td>Div. Liquida/EBITDA</td><td>1,90</td></tr>
          <tr><td>Div. Yield</td><td>6,30%</td></tr>
          <tr><td>Payout</td><td>55,00%</td></tr>
          <tr><td>Receita Liquida</td><td>1.234.567</td></tr>
          <tr><td>Lucro Liquido</td><td>123.456</td></tr>
          <tr><td>Valor de mercado</td><td>9.876.543</td></tr>
        </table>
        """

        payload = extract_fundamentus_indicators(html)

        self.assertEqual(payload["pe_ratio"], 10.5)
        self.assertEqual(payload["pvp"], 1.23)
        self.assertEqual(payload["ev_ebitda"], 7.8)
        self.assertEqual(payload["roe"], 16.2)
        self.assertEqual(payload["roic"], 12.1)
        self.assertEqual(payload["net_margin"], 18.4)
        self.assertEqual(payload["debt_to_ebitda"], 1.9)
        self.assertEqual(payload["dividend_yield"], 6.3)
        self.assertEqual(payload["payout"], 55)
        self.assertEqual(payload["revenue"], 1234567)
        self.assertEqual(payload["profit"], 123456)
        self.assertEqual(payload["market_value"], 9876543)

    def test_fundamentus_provider_is_disabled_by_default(self) -> None:
        provider = FundamentusProviderV2()
        provider.settings.fundamentus_enabled = False

        self.assertFalse(
            provider.supports(
                "fundamentals",
                MarketDataRequest(symbol="ITSA4", market="B3", asset_class="Acoes", currency="BRL"),
            )
        )

    def test_provider_failure_records_event_and_falls_back(self) -> None:
        engine = MarketDataEngine(db=self.db, provider_manager=ProviderManager([MockMarketDataProviderV2()]))
        engine.provider_manager = ProviderManager(
            [FailingProvider(), MockMarketDataProviderV2()],
            on_provider_error=engine._record_provider_error,
        )

        quote = engine.get_quote("WEGE3", market="B3", asset_class="Acoes", currency="BRL")

        events = self.db.execute(select(MarketDataProviderEvent)).scalars().all()
        self.assertEqual(quote.provider, "mock")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].provider, "failing")
        self.assertEqual(events[0].event_type, "RuntimeError")

    def test_knowledge_engine_saves_fundamentus_facts_and_marks_divergence(self) -> None:
        asset = Asset(
            ticker="ITSA4",
            name="Itausa PN",
            asset_class="Acoes",
            sector="Holding financeira",
            segment="Financeiro",
            currency="BRL",
            provider_symbol="ITSA4",
            last_price=Decimal("10.00"),
        )
        self.db.add(asset)
        self.db.flush()
        request = MarketDataRequest(symbol="ITSA4", asset_id=asset.id, market="B3", asset_class="Acoes", currency="BRL")
        brapi_data = normalize_fundamentals(
            "brapi",
            request,
            raw={"priceEarnings": 10, "returnOnEquity": 10, "dividendYield": 5},
            currency="BRL",
        )
        fundamentus_data = normalize_fundamentals(
            "fundamentus",
            request,
            raw={"pe_ratio": 14, "roe": 10.5, "dividend_yield": 5.1},
            currency="BRL",
        )

        knowledge = KnowledgeEngine()
        knowledge.save_market_data(self.db, asset.id, brapi_data)
        knowledge.save_market_data(self.db, asset.id, fundamentus_data)

        facts = self.db.execute(select(AssetFact).where(AssetFact.source == "fundamentus")).scalars().all()
        divergences = self.db.execute(select(AssetMetricDivergence)).scalars().all()
        self.assertTrue(any(fact.metric_key == "pe_ratio" for fact in facts))
        self.assertEqual(len(divergences), 1)
        self.assertEqual(divergences[0].metric_key, "pe_ratio")
        self.assertEqual(float(divergences[0].primary_value), 10)
        self.assertEqual(float(divergences[0].comparison_value), 14)


if __name__ == "__main__":
    unittest.main()
