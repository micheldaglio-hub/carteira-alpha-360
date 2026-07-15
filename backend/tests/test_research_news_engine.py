from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, AssetFact, MarketSnapshot, Transaction, User
from app.wealth_os import research_news_engine
from app.wealth_os.research_news_engine import build_asset_research_report, build_research_center


class ResearchNewsEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="research@carteiraalpha.com", full_name="Research User", password_hash="hash")
        self.db.add(self.user)
        self.db.flush()
        self.asset = Asset(
            ticker="BBSE3",
            name="BB Seguridade",
            asset_class="Acoes",
            sector="Seguros",
            segment="Seguridade",
            last_price=Decimal("35.00"),
            provider_symbol="BBSE3",
            market="B3",
        )
        self.db.add(self.asset)
        self.db.flush()
        self.db.add(
            MarketSnapshot(
                asset_id=self.asset.id,
                price=Decimal("35.00"),
                dividend_yield=Decimal("7.5"),
                payout=Decimal("80"),
                roe=Decimal("30"),
                pe_ratio=Decimal("9"),
                pvp=Decimal("3"),
            )
        )
        self.db.add(
            AssetFact(
                asset_id=self.asset.id,
                source="brapi",
                metric_key="dividend_yield",
                value_numeric=Decimal("7.5"),
                value_text="7.5",
                unit="percent",
                period="latest",
                confidence=Decimal("85"),
                as_of=datetime.now(UTC),
            )
        )
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=self.asset.id,
                type="buy",
                date=datetime.now(UTC).date(),
                quantity=Decimal("10"),
                price=Decimal("35"),
                fees=Decimal("0"),
                broker="Alpha",
            )
        )
        self.db.commit()
        self.original_fetch_news = research_news_engine._fetch_news
        research_news_engine._fetch_news = lambda db, asset, refresh=False: []

    def tearDown(self) -> None:
        research_news_engine._fetch_news = self.original_fetch_news
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_asset_research_report_uses_internal_evidence(self) -> None:
        report = build_asset_research_report(self.db, self.user.id, "BBSE3")

        self.assertEqual(report.ticker, "BBSE3")
        self.assertGreater(report.researchScore, 0)
        self.assertTrue(report.evidence)
        self.assertTrue(any(item.source in {"brapi", "market_snapshot"} for item in report.evidence))
        self.assertIn(report.confidence, {"baixa", "media", "alta"})

    def test_research_center_builds_coverage(self) -> None:
        center = build_research_center(self.db, self.user.id, limit=4)

        self.assertEqual(center.status, "operacional")
        self.assertGreaterEqual(center.coverage["assets"], 1)
        self.assertIn("withEvidence", center.coverage)
        self.assertTrue(center.sourceHealth)

    def test_missing_asset_report_is_safe(self) -> None:
        report = build_asset_research_report(self.db, self.user.id, "NAOEXISTE")

        self.assertEqual(report.status, "ativo_nao_encontrado")
        self.assertEqual(report.researchScore, 0)
        self.assertTrue(report.dataGaps)


if __name__ == "__main__":
    unittest.main()

