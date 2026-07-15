from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, MarketSnapshot, Transaction, User
from app.wealth_os.strategy_engine import build_strategy_report


class StrategyEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="strategy@carteiraalpha.com", full_name="Strategy User", password_hash="hash")
        self.db.add(self.user)
        self.db.flush()

        assets = [
            Asset(
                ticker="TAEE11",
                name="Taesa",
                asset_class="Acoes",
                sector="Energia",
                segment="Transmissao",
                currency="BRL",
                country_code="BR",
                region="Brasil",
                last_price=Decimal("42.00"),
            ),
            Asset(
                ticker="HGLG11",
                name="CSHG Logistica",
                asset_class="FIIs",
                sector="Fundos imobiliarios",
                segment="Logistica",
                currency="BRL",
                country_code="BR",
                region="Brasil",
                last_price=Decimal("165.00"),
            ),
            Asset(
                ticker="AAPL",
                name="Apple",
                asset_class="Stocks",
                sector="Tecnologia",
                currency="USD",
                country_code="US",
                region="America do Norte",
                market="NASDAQ",
                last_price=Decimal("210.00"),
            ),
            Asset(
                ticker="BTC",
                name="Bitcoin",
                asset_class="Cripto",
                sector="Cripto",
                currency="USD",
                market="Crypto",
                last_price=Decimal("65000.00"),
            ),
        ]
        self.db.add_all(assets)
        self.db.flush()
        for asset in assets:
            self.db.add(
                MarketSnapshot(
                    asset_id=asset.id,
                    price=asset.last_price,
                    dividend_yield=Decimal("8.0") if asset.ticker in {"TAEE11", "HGLG11"} else Decimal("0"),
                )
            )

        transactions = [
            ("TAEE11", Decimal("10"), Decimal("40.00")),
            ("HGLG11", Decimal("2"), Decimal("160.00")),
            ("AAPL", Decimal("1"), Decimal("200.00")),
            ("BTC", Decimal("0.003"), Decimal("60000.00")),
        ]
        by_ticker = {asset.ticker: asset for asset in assets}
        for ticker, quantity, price in transactions:
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

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_strategy_report_scores_profiles_without_ui_dependency(self) -> None:
        report = build_strategy_report(self.db, self.user.id)

        self.assertEqual(report.status, "operacional")
        self.assertGreaterEqual(report.primaryScore, 0)
        self.assertTrue(report.assessments)
        self.assertTrue(report.rules)

        strategy_ids = {item.strategy.id for item in report.assessments}
        self.assertIn("dividendos", strategy_ids)
        self.assertIn("crescimento", strategy_ids)
        self.assertIn("global", strategy_ids)
        self.assertIn("cripto_controlado", strategy_ids)
        self.assertIn("bogle", strategy_ids)

    def test_strategy_report_normalizes_global_and_crypto_allocations(self) -> None:
        report = build_strategy_report(self.db, self.user.id)

        self.assertGreater(report.currentAllocation.get("Global", 0), 0)
        self.assertGreater(report.currentAllocation.get("Cripto", 0), 0)
        self.assertIn("globalExposure", report.metrics)
        self.assertIn("cryptoWeight", report.metrics)

        primary = report.assessments[0]
        self.assertTrue(primary.factors)
        self.assertTrue(primary.assetFits)
        self.assertTrue(all(item.reading for item in primary.assetFits))


if __name__ == "__main__":
    unittest.main()
