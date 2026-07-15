from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, MarketSnapshot, Transaction, User
from app.schemas import DashboardProjectionPremises
from app.services.projection_premises import save_dashboard_projection_premises
from app.wealth_os.copilot_service import answer_question, ask_copilot, copilot_status
from app.wealth_os.data_confidence_engine import build_data_confidence
from app.wealth_os.event_engine_v2 import build_event_payload_v2
from app.wealth_os.goal_engine import build_goals
from app.wealth_os.guardian_engine import build_guardian_report
from app.wealth_os.service import build_command_center


class WealthOsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="wealth@carteiraalpha.com", full_name="Wealth User", password_hash="hash")
        self.db.add(self.user)
        self.db.flush()

        asset = Asset(
            ticker="TAEE11",
            name="Taesa",
            asset_class="Acoes",
            sector="Energia",
            segment="Transmissao",
            last_price=Decimal("42.00"),
            provider_symbol="TAEE11",
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(MarketSnapshot(asset_id=asset.id, price=Decimal("42.00"), dividend_yield=Decimal("8.5")))
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 7, 1),
                quantity=Decimal("10"),
                price=Decimal("40.00"),
                fees=Decimal("0"),
                broker="Alpha",
            )
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_command_center_returns_core_blocks(self) -> None:
        payload = build_command_center(self.db, self.user.id)

        self.assertGreaterEqual(payload.totalWealth, 420)
        self.assertTrue(payload.topGoals)
        self.assertTrue(payload.dataConfidence)
        self.assertTrue(payload.copilotQuestions)
        self.assertGreaterEqual(payload.wealthProgressScore.score, 0)

    def test_goal_engine_uses_saved_dashboard_premises(self) -> None:
        save_dashboard_projection_premises(
            self.db,
            self.user.id,
            DashboardProjectionPremises(monthly_contribution=300, monthly_return=1.2),
        )

        goals = build_goals(self.db, self.user.id)
        first_million = next(goal for goal in goals if goal.id == "first_1m")

        self.assertEqual(first_million.assumptions[0], "Nao e promessa de retorno; e uma simulacao com aporte e retorno informados.")
        self.assertIsNotNone(first_million.estimatedMonths)

    def test_data_confidence_handles_empty_portfolio(self) -> None:
        empty_user = User(email="empty@carteiraalpha.com", full_name="Empty User", password_hash="hash")
        self.db.add(empty_user)
        self.db.commit()

        confidence = build_data_confidence(self.db, empty_user.id)

        self.assertEqual(confidence[0].status, "vazio")
        self.assertEqual(confidence[0].confidenceScore, 0)

    def test_copilot_answer_is_structured(self) -> None:
        answer = answer_question(self.db, self.user.id, "largest_asset")

        self.assertEqual(answer["id"], "largest_asset")
        self.assertIn("TAEE11", answer["answer"])
        self.assertTrue(answer["dataUsed"])

    def test_copilot_chat_uses_internal_citations(self) -> None:
        answer = ask_copilot(self.db, self.user.id, "Explique minha carteira e o maior risco agora")

        self.assertEqual(answer["mode"], "deterministic")
        self.assertEqual(answer["provider"], "internal")
        self.assertTrue(answer["answer"])
        self.assertTrue(answer["citations"])
        self.assertTrue(answer["dataUsed"])
        self.assertNotIn("compre agora", answer["answer"].lower())

    def test_copilot_status_defaults_to_safe_fallback(self) -> None:
        status = copilot_status()

        self.assertEqual(status["status"], "deterministic_fallback")
        self.assertFalse(status["aiEnabled"])
        self.assertTrue(status["rules"])

    def test_guardian_report_is_human_monitoring_queue(self) -> None:
        report = build_guardian_report(self.db, self.user.id)

        self.assertIn(report.status, {"critico", "atencao", "estavel"})
        self.assertIn("Guardian 2.0", report.headline)
        self.assertIn("total", report.summary)
        self.assertTrue(all(item.recommendedAction for item in report.items))

    def test_event_engine_v2_keeps_alerts_contract(self) -> None:
        payload = build_event_payload_v2(self.db, self.user.id)

        self.assertIn("summary", payload)
        self.assertIn("alerts", payload)
        self.assertGreaterEqual(payload["summary"]["total"], len(payload["alerts"]))
        if payload["alerts"]:
            first = payload["alerts"][0]
            self.assertIn("eventType", first)
            self.assertIn("recommendedAction", first)
            self.assertIn("confidence", first)


if __name__ == "__main__":
    unittest.main()
