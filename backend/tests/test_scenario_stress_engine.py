from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, MarketSnapshot, Transaction, User
from app.wealth_os import scenario_engine
from app.wealth_os.scenario_engine import build_scenarios, build_stress_test_report


class ScenarioStressEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="stress@carteiraalpha.com", full_name="Stress User", password_hash="hash")
        self.db.add(self.user)
        self.db.flush()

        assets = [
            Asset(ticker="TAEE11", name="Taesa", asset_class="Acoes", sector="Energia", currency="BRL", country_code="BR", last_price=Decimal("40")),
            Asset(ticker="HGLG11", name="HGLG", asset_class="FIIs", sector="Fundos imobiliarios", currency="BRL", country_code="BR", last_price=Decimal("160")),
            Asset(ticker="AAPL", name="Apple", asset_class="Stocks", sector="Tecnologia", currency="USD", country_code="US", market="NASDAQ", last_price=Decimal("200")),
            Asset(ticker="BTC", name="Bitcoin", asset_class="Cripto", sector="Cripto", currency="USD", market="Crypto", last_price=Decimal("60000")),
        ]
        self.db.add_all(assets)
        self.db.flush()
        for asset in assets:
            self.db.add(MarketSnapshot(asset_id=asset.id, price=asset.last_price, dividend_yield=Decimal("8") if asset.ticker in {"TAEE11", "HGLG11"} else Decimal("0")))

        by_ticker = {asset.ticker: asset for asset in assets}
        rows = [
            ("TAEE11", Decimal("10"), Decimal("38")),
            ("HGLG11", Decimal("2"), Decimal("155")),
            ("AAPL", Decimal("1"), Decimal("190")),
            ("BTC", Decimal("0.004"), Decimal("50000")),
        ]
        for ticker, quantity, price in rows:
            self.db.add(
                Transaction(
                    user_id=self.user.id,
                    asset_id=by_ticker[ticker].id,
                    type="buy",
                    date=date(2026, 7, 1),
                    quantity=quantity,
                    price=price,
                    fees=Decimal("0"),
                    broker="Alpha",
                )
            )
        self.db.commit()

        self.original_macro = scenario_engine.build_macro_fx_snapshot
        scenario_engine.build_macro_fx_snapshot = lambda db, user_id, refresh=False: SimpleNamespace(
            headline="Macro mockado para teste.",
            indicators=[
                SimpleNamespace(title="Selic meta", value=15.0, unit="% a.a.", status="alto"),
                SimpleNamespace(title="IPCA acumulado 12m", value=6.0, unit="% a.a.", status="alto"),
            ],
            fxRates=[SimpleNamespace(pair="USD/BRL", rate=5.5, status="atualizado")],
        )

    def tearDown(self) -> None:
        scenario_engine.build_macro_fx_snapshot = self.original_macro
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_stress_report_contains_advanced_scenarios(self) -> None:
        report = build_stress_test_report(self.db, self.user.id)

        self.assertEqual(report.status, "operacional")
        self.assertGreater(report.baseEquity, 0)
        self.assertGreaterEqual(len(report.scenarios), 8)
        self.assertTrue(report.macroContext)
        self.assertIn("black_swan_global", {item.id for item in report.scenarios})
        self.assertLessEqual(report.worstImpactPct, 0)
        self.assertGreaterEqual(report.resilienceScore, 0)

    def test_scenarios_preserve_legacy_fields_and_add_bucket_impacts(self) -> None:
        scenarios = build_scenarios(self.db, self.user.id)
        first = scenarios[0]

        self.assertTrue(first.id)
        self.assertTrue(first.title)
        self.assertIsInstance(first.impactValue, float)
        self.assertIsInstance(first.impactPct, float)
        self.assertTrue(first.bucketImpacts)
        self.assertTrue(first.recommendedActions)
        self.assertGreaterEqual(first.shockedEquity, first.stressedEquity)

    def test_crypto_winter_hits_crypto_bucket(self) -> None:
        report = build_stress_test_report(self.db, self.user.id)
        crypto = next(item for item in report.scenarios if item.id == "crypto_winter_70")
        crypto_bucket = next(item for item in crypto.bucketImpacts if item["bucket"] == "Cripto")

        self.assertEqual(crypto_bucket["shockPct"], -70)
        self.assertLess(crypto_bucket["impactValue"], 0)
        self.assertEqual(crypto.category, "cripto")


if __name__ == "__main__":
    unittest.main()
