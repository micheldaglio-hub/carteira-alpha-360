from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, DataEvidenceLedger, User
from app.services.data_lineage import data_lineage_summary, evidence_to_dict, list_data_evidence, record_data_evidence
from app.services.data_lineage_integrations import (
    record_dashboard_evidence,
    record_projection_evidence,
    record_tax_evidence,
)


class DataLineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="lineage@carteiraalpha.com", full_name="Lineage User", password_hash="hash")
        self.asset = Asset(ticker="BBSE3", name="BB Seguridade", asset_class="Acoes", sector="Seguros", last_price=42)
        self.db.add_all([self.user, self.asset])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_records_and_lists_data_evidence(self) -> None:
        evidence = record_data_evidence(
            self.db,
            domain="market_data",
            field_name="price",
            user_id=self.user.id,
            asset_id=self.asset.id,
            value_numeric=42.25,
            currency="BRL",
            provider="brapi",
            source_type="provider",
            source_ref="quote:BBSE3",
            confidence=88,
            quality_score=91,
            metadata={"ticker": "BBSE3"},
        )
        self.db.commit()

        rows = list_data_evidence(self.db, user_id=self.user.id, domain="market_data")
        payload = evidence_to_dict(evidence)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].field_name, "price")
        self.assertEqual(payload["provider"], "brapi")
        self.assertEqual(payload["metadata"]["ticker"], "BBSE3")

    def test_summary_penalizes_fallback_and_low_confidence(self) -> None:
        record_data_evidence(
            self.db,
            domain="portfolio_backtest",
            field_name="totalReturnPct",
            user_id=self.user.id,
            value_numeric=10,
            provider="portfolio_backtest_engine",
            source_type="formula",
            confidence=90,
            quality_score=90,
        )
        record_data_evidence(
            self.db,
            domain="market_data",
            field_name="history",
            user_id=self.user.id,
            asset_id=self.asset.id,
            provider="fallback_current_price",
            source_type="fallback",
            confidence=40,
            quality_score=40,
            status="fallback",
        )
        self.db.commit()

        summary = data_lineage_summary(self.db, user_id=self.user.id)

        self.assertEqual(summary["totalEvidence"], 2)
        self.assertEqual(summary["fallbackEvidence"], 1)
        self.assertEqual(summary["lowConfidenceEvidence"], 1)
        self.assertLess(summary["score"], 100)

    def test_global_evidence_is_visible_to_user(self) -> None:
        record_data_evidence(
            self.db,
            domain="financial_formula_audit",
            field_name="audit_score",
            value_numeric=100,
            provider="financial_formula_auditor",
            source_type="formula",
            confidence=100,
            quality_score=100,
        )
        self.db.commit()

        rows = list_data_evidence(self.db, user_id=self.user.id, domain="financial_formula_audit")

        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].user_id)
        self.assertEqual(self.db.query(DataEvidenceLedger).count(), 1)

    def test_dashboard_integration_records_metrics_and_fixed_income(self) -> None:
        payload = {
            "metrics": {
                "totalEquity": 42000,
                "investedValue": 41000,
                "pnl": 1000,
                "pnlPct": 2.43,
                "projectedPassiveIncome": 420,
                "projectedProceedsIncome": 20,
                "projectedFixedIncome": 400,
                "proceedsYear": 120,
                "projection10y": 100000,
                "projection20y": 300000,
                "projection30y": 900000,
            },
            "portfolioSnapshot": {
                "allocations": {"byClass": [{"name": "Renda fixa", "value": 40000}]},
                "positions": [
                    {
                        "assetId": self.asset.id,
                        "ticker": "RDB",
                        "class": "Renda fixa",
                        "currentValue": 40826.84,
                        "pnl": 18.2,
                        "returnPct": 0.04,
                        "fixedIncome": {"source": "Banco Central SGS 12", "dailyRatePct": 0.041, "appliedDays": 12},
                    }
                ],
            },
        }

        result = record_dashboard_evidence(self.db, self.user.id, payload)
        rows = list_data_evidence(self.db, user_id=self.user.id, domain="dashboard")
        fixed_rows = list_data_evidence(self.db, user_id=self.user.id, domain="fixed_income")

        self.assertEqual(result["status"], "recorded")
        self.assertGreaterEqual(len(rows), 8)
        self.assertGreaterEqual(len(fixed_rows), 4)

    def test_projection_integration_records_formula_outputs(self) -> None:
        result = {
            "summary": {"finalValue": 100000, "totalContributed": 25000, "totalProceeds": 7000, "estimatedYearsToGoal": 12.5},
            "breakdown": {"capitalGain": 68000, "totalReturn": 75000, "finalReal": 62000},
            "independence": {"monthlyPassiveIncome": 625, "requiredWealth": 800000, "remainingWealth": 758000},
        }

        status = record_projection_evidence(self.db, self.user.id, {"years": 20}, result, 42000)
        rows = list_data_evidence(self.db, user_id=self.user.id, domain="financial_projection")

        self.assertEqual(status["status"], "recorded")
        self.assertTrue(any(row.field_name == "finalValue" for row in rows))
        self.assertTrue(any(row.formula_name == "financial_projection_engine.monthlyPassiveIncome" for row in rows))

    def test_tax_integration_records_estimated_taxes(self) -> None:
        report = {
            "period": "2026-07",
            "jurisdiction": "BR",
            "status": "estimativa_operacional",
            "grossIncome": 100,
            "realizedGain": 250,
            "estimatedWithheldTax": 15,
            "estimatedTaxDue": 37.5,
            "netIncomeAfterEstimatedTax": 297.5,
            "items": [{"id": "income_jcp"}],
            "rules": [{"id": "br_jcp_irrf"}],
        }

        status = record_tax_evidence(self.db, self.user.id, report)
        rows = list_data_evidence(self.db, user_id=self.user.id, domain="tax")

        self.assertEqual(status["status"], "recorded")
        self.assertEqual(len(rows), 5)
        self.assertTrue(any(row.field_name == "estimatedWithheldTax" for row in rows))


if __name__ == "__main__":
    unittest.main()
