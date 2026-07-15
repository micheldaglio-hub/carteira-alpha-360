from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import BillingCheckoutSession, BillingTransaction, BillingWebhookEvent, User
from app.services.rbac import grant_role_to_user


class BillingGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="billing@alpha.local", full_name="Billing User", password_hash="hash")
        self.db.add(self.user)
        self.db.commit()
        grant_role_to_user(self.db, user_id=self.user.id, role="free_user", source="test", commit=True)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.headers = {"Authorization": f"Bearer {create_access_token(self.user.id)}"}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_mock_checkout_activates_premium_subscription(self) -> None:
        checkout = self.client.post(
            "/api/billing/checkout/sessions",
            json={"plan_code": "alpha_premium", "billing_cycle": "monthly"},
            headers=self.headers,
        )
        self.assertEqual(checkout.status_code, 201)
        checkout_payload = checkout.json()
        session_id = checkout_payload["checkout"]["id"]
        self.assertEqual(checkout_payload["checkout"]["provider"], "mock")
        self.assertEqual(checkout_payload["checkout"]["status"], "pending")

        paid = self.client.post(f"/api/billing/mock/checkout/{session_id}/success", headers=self.headers)
        self.assertEqual(paid.status_code, 200)
        self.assertFalse(paid.json()["duplicate"])
        self.assertEqual(paid.json()["transaction"]["status"], "paid")

        access = self.client.get("/api/premium/subscriptions/me", headers=self.headers)
        self.assertEqual(access.status_code, 200)
        active_keys = {item["entitlementKey"] for item in access.json()["activeEntitlements"]}
        self.assertIn("premium.research.read", active_keys)
        self.assertIn("premium.pdf.download", active_keys)

        billing = self.client.get("/api/billing/me", headers=self.headers)
        self.assertEqual(billing.status_code, 200)
        self.assertEqual(len(billing.json()["checkouts"]), 1)
        self.assertEqual(len(billing.json()["transactions"]), 1)

        sessions = self.db.execute(select(BillingCheckoutSession)).scalars().all()
        transactions = self.db.execute(select(BillingTransaction)).scalars().all()
        webhooks = self.db.execute(select(BillingWebhookEvent)).scalars().all()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].status, "paid")
        self.assertEqual(len(transactions), 1)
        self.assertEqual(len(webhooks), 1)

    def test_mock_webhook_is_idempotent(self) -> None:
        checkout = self.client.post(
            "/api/billing/checkout/sessions",
            json={"plan_code": "alpha_premium", "billing_cycle": "annual"},
            headers=self.headers,
        ).json()
        session_id = checkout["checkout"]["id"]

        first = self.client.post(f"/api/billing/mock/checkout/{session_id}/success", headers=self.headers)
        second = self.client.post(f"/api/billing/mock/checkout/{session_id}/success", headers=self.headers)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.json()["duplicate"])
        self.assertTrue(second.json()["duplicate"])
        transactions = self.db.execute(select(BillingTransaction)).scalars().all()
        webhooks = self.db.execute(select(BillingWebhookEvent)).scalars().all()
        self.assertEqual(len(transactions), 1)
        self.assertEqual(len(webhooks), 1)


if __name__ == "__main__":
    unittest.main()
