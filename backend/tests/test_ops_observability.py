from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User
from app.services.audit import audit_summary, list_audit_events, write_audit_event
from app.services.job_runner import execute_job, job_status, registry, run_formula_audit, run_heartbeat


class OpsObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="ops@carteiraalpha.com", full_name="Ops User", password_hash="hash")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_audit_event_is_persisted_and_listed(self) -> None:
        event = write_audit_event(
            self.db,
            event_type="test_event",
            category="tests",
            action="unit_test",
            user_id=self.user.id,
            message="Evento de auditoria para teste.",
        )

        self.assertIsNotNone(event)
        events = list_audit_events(self.db, user_id=self.user.id)
        summary = audit_summary(self.db, user_id=self.user.id)

        self.assertEqual(len(events), 1)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(events[0].event_type, "test_event")

    def test_job_execution_records_run(self) -> None:
        result = execute_job(self.db, "ops.heartbeat", run_heartbeat)
        status = job_status(self.db)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["jobName"], "ops.heartbeat")
        self.assertIn("ops.heartbeat", status["registeredJobs"])
        self.assertIsNotNone(status["latestRuns"]["ops.heartbeat"])

    def test_registry_contains_data_jobs_and_formula_audit(self) -> None:
        names = registry.names()

        self.assertIn("market_data.user_assets", names)
        self.assertIn("market_data.model_portfolios", names)
        self.assertIn("macro_fx.refresh", names)
        self.assertIn("financial.formula_audit", names)

    def test_formula_audit_job_records_success(self) -> None:
        result = execute_job(self.db, "financial.formula_audit", run_formula_audit)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["jobName"], "financial.formula_audit")
        self.assertEqual(result["details"]["report"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
