from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, Dividend
from app.services.data_confidence_engine import build_data_confidence_audit
from app.services.portfolio_backtest import build_current_portfolio_backtest_series
from app.services.recommendation_governance_engine import build_recommendation_governance
from app.services.total_return_engine import apply_total_return_overlay


class TotalReturnGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_total_return_adds_dividends_without_treating_contribution_as_profit(self) -> None:
        asset = Asset(ticker="TEST3", name="Teste", asset_class="Acoes", sector="Energia", last_price=Decimal("12"))
        self.db.add(asset)
        self.db.flush()
        self.db.add(
            Dividend(
                user_id="user-1",
                asset_id=asset.id,
                date=date(2025, 2, 15),
                amount_per_share=Decimal("0.50"),
                total_amount=Decimal("50.00"),
                source="dividend",
            )
        )
        self.db.commit()

        positions = [{"assetId": asset.id, "ticker": "TEST3", "class": "Acoes", "quantity": 100, "currentPrice": 12}]
        histories = {
            asset.id: [
                {"date": date(2025, 1, 1), "close": 10},
                {"date": date(2025, 1, 31), "close": 10},
                {"date": date(2025, 2, 28), "close": 11},
            ]
        }
        rows = build_current_portfolio_backtest_series(
            positions,
            histories,
            date(2025, 1, 1),
            date(2025, 2, 28),
            baseline_by_asset={asset.id: 1000},
            monthly_contribution=200,
        )

        enriched, report = apply_total_return_overlay(self.db, "user-1", positions, rows, date(2025, 1, 1), date(2025, 2, 28))

        self.assertEqual(rows[-1]["cumulativeReturnPct"], 10)
        self.assertEqual(report["incomeTotal"], 50)
        self.assertEqual(report["breakdown"]["dividend"], 50)
        self.assertGreater(enriched[-1]["stocksTotalReturnPct"], enriched[-1]["stocksReturnPct"])
        self.assertEqual(enriched[-1]["incomeTotal"], 50)

    def test_total_return_does_not_duplicate_income_in_start_month(self) -> None:
        asset = Asset(ticker="JAN3", name="Janeiro", asset_class="Acoes", sector="Energia", last_price=Decimal("10"))
        self.db.add(asset)
        self.db.flush()
        self.db.add(
            Dividend(
                user_id="user-1",
                asset_id=asset.id,
                date=date(2025, 1, 15),
                amount_per_share=Decimal("0.10"),
                total_amount=Decimal("10.00"),
                source="jcp",
            )
        )
        self.db.commit()

        positions = [{"assetId": asset.id, "ticker": "JAN3", "class": "Acoes", "quantity": 100, "currentPrice": 10}]
        histories = {
            asset.id: [
                {"date": date(2025, 1, 1), "close": 10},
                {"date": date(2025, 1, 31), "close": 10},
            ]
        }
        rows = build_current_portfolio_backtest_series(positions, histories, date(2025, 1, 1), date(2025, 1, 31))

        enriched, report = apply_total_return_overlay(self.db, "user-1", positions, rows, date(2025, 1, 1), date(2025, 1, 31))

        self.assertEqual(report["incomeTotal"], 10)
        self.assertEqual(enriched[0]["incomeTotal"], 0)
        self.assertEqual(enriched[1]["incomeTotal"], 10)

    def test_data_confidence_reports_fallback_fields(self) -> None:
        asset = Asset(ticker="LOW3", name="Low Confidence", asset_class="Acoes", sector="Bancos", last_price=Decimal("10"))
        self.db.add(asset)
        self.db.commit()

        audit = build_data_confidence_audit(self.db, "user-1")

        self.assertEqual(audit["status"], "operational")
        self.assertEqual(audit["assetCount"], 0)
        self.assertIn("Data Confidence", audit["title"])

    def test_recommendation_governance_builds_review_trail(self) -> None:
        recommended_report = {
            "reportMonth": "2026-07",
            "nextReviewDate": "2026-08-01",
            "institutionalScore": 84,
            "assetReports": [
                {
                    "ticker": "BBSE3",
                    "name": "BB Seguridade",
                    "assetClass": "Acoes",
                    "role": "Renda passiva",
                    "institutionalScore": 86,
                    "classification": "Nucleo institucional",
                    "riskLevel": "moderado",
                    "thesis": "Empresa de seguros com alta rentabilidade e historico de distribuicao.",
                    "evidence": ["ROE elevado", "Historico de proventos"],
                    "risks": ["Dependencia do Banco do Brasil"],
                }
            ],
        }
        confidence_report = {"overallScore": 82}
        data_audit = {"overallScore": 76, "fallbackAssetCount": 0, "assetRows": []}

        governance = build_recommendation_governance(None, None, recommended_report, confidence_report, data_audit)

        self.assertEqual(governance["title"], "Recommendation Governance Engine")
        self.assertEqual(governance["reportMonth"], "2026-07")
        self.assertEqual(governance["assetCount"], 1)
        self.assertTrue(governance["assetReviews"][0]["thesis"])
        self.assertTrue(governance["extraordinaryReviewTriggers"])


if __name__ == "__main__":
    unittest.main()
