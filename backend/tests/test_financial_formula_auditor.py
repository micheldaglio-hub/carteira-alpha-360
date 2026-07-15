from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AuditEvent, DataEvidenceLedger
from app.services.financial_formula_auditor import run_financial_formula_audit


class FinancialFormulaAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_formula_audit_passes_known_deterministic_cases(self) -> None:
        report = run_financial_formula_audit()

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["score"], 100)
        self.assertGreaterEqual(report["passed"], 6)
        self.assertEqual(report["failed"], 0)
        self.assertTrue(all(case["status"] == "pass" for case in report["cases"]))

    def test_formula_audit_writes_operational_audit_event(self) -> None:
        report = run_financial_formula_audit(self.db)
        event = self.db.query(AuditEvent).filter(AuditEvent.event_type == "financial_formula_audit").one()
        evidence_count = self.db.query(DataEvidenceLedger).filter(DataEvidenceLedger.domain == "financial_formula_audit").count()

        self.assertEqual(report["status"], "pass")
        self.assertEqual(event.category, "financial_audit")
        self.assertEqual(event.severity, "info")
        self.assertIn("100", event.message)
        self.assertGreaterEqual(evidence_count, 7)


if __name__ == "__main__":
    unittest.main()
