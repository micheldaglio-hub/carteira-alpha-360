from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import (
    PremiumAccessLog,
    PublicationApproval,
    PublicationArtifact,
    PublicationReview,
    PublicationVersion,
    ResearchPublication,
    User,
)
from app.premium_research.entitlements import (
    DOWNLOAD_ACTION,
    authorize_premium_artifact_access,
    grant_subscription_to_user,
    seed_default_subscription_plans,
)
from app.premium_research.pdf_publisher import render_pdf_from_html_artifact
from app.premium_research.publisher import create_premium_research_draft
from app.premium_research.renderer import render_publication_snapshot
from app.premium_research.snapshot_engine import create_publication_snapshot
from app.services.rbac import grant_role_to_user
from tests.test_publication_snapshots import _source_payload


class PremiumEntitlementsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.owner = User(email="premium-owner@alpha.local", full_name="Owner User", password_hash="hash")
        self.subscriber = User(email="premium-subscriber@alpha.local", full_name="Subscriber User", password_hash="hash")
        self.db.add_all([self.owner, self.subscriber])
        self.db.commit()
        grant_role_to_user(self.db, user_id=self.owner.id, role="admin", source="test", commit=True)
        grant_role_to_user(self.db, user_id=self.subscriber.id, role="free_user", source="test", commit=True)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.owner_headers = {"Authorization": f"Bearer {create_access_token(self.owner.id)}"}
        self.subscriber_headers = {"Authorization": f"Bearer {create_access_token(self.subscriber.id)}"}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_seed_grant_and_authorize_pdf_download(self) -> None:
        pdf_artifact = self._create_pdf_artifact()
        plans = seed_default_subscription_plans(self.db, commit=True)
        denied = authorize_premium_artifact_access(
            self.db,
            user_id=self.subscriber.id,
            artifact=pdf_artifact,
            action=DOWNLOAD_ACTION,
            commit=True,
        )
        granted = grant_subscription_to_user(
            self.db,
            user_id=self.subscriber.id,
            plan_code="alpha_premium",
            period_days=30,
            commit=True,
        )
        allowed = authorize_premium_artifact_access(
            self.db,
            user_id=self.subscriber.id,
            artifact=pdf_artifact,
            action=DOWNLOAD_ACTION,
            commit=True,
        )
        logs = self.db.execute(select(PremiumAccessLog).where(PremiumAccessLog.user_id == self.subscriber.id)).scalars().all()

        self.assertEqual(len(plans), 3)
        self.assertFalse(denied["allowed"])
        self.assertEqual(denied["reason"], "missing_active_entitlement")
        self.assertEqual(granted["subscription"]["planCode"], "alpha_premium")
        self.assertTrue(any(item["entitlementKey"] == "premium.pdf.download" for item in granted["entitlements"]))
        self.assertTrue(allowed["allowed"])
        self.assertEqual(allowed["reason"], "active_entitlement")
        self.assertEqual(len(logs), 2)

    def test_subscriber_download_requires_active_entitlement(self) -> None:
        pdf_artifact = self._create_pdf_artifact()

        blocked = self.client.get(
            f"/api/premium/artifacts/{pdf_artifact.id}/download",
            headers=self.subscriber_headers,
        )
        self.assertEqual(blocked.status_code, 403)

        self_grant = self.client.post(
            "/api/premium/subscriptions/grant",
            json={"plan_code": "alpha_premium", "period_days": 30},
            headers=self.subscriber_headers,
        )
        self.assertEqual(self_grant.status_code, 403)

        grant = self.client.post(
            "/api/premium/subscriptions/grant",
            json={"user_id": self.subscriber.id, "plan_code": "alpha_premium", "period_days": 30},
            headers=self.owner_headers,
        )
        self.assertEqual(grant.status_code, 201)
        self.assertEqual(grant.json()["subscription"]["planCode"], "alpha_premium")

        downloaded = self.client.get(
            f"/api/premium/artifacts/{pdf_artifact.id}/download",
            headers=self.subscriber_headers,
        )
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.headers["content-type"], "application/pdf")
        self.assertTrue(downloaded.content.startswith(b"%PDF"))

        access = self.client.get("/api/premium/subscriptions/me", headers=self.subscriber_headers)
        self.assertEqual(access.status_code, 200)
        self.assertGreaterEqual(len(access.json()["activeEntitlements"]), 1)

        logs = self.client.get("/api/premium/access-logs", headers=self.subscriber_headers)
        self.assertEqual(logs.status_code, 200)
        self.assertGreaterEqual(logs.json()["count"], 2)

        home = self.client.get("/api/premium/subscriber/home", headers=self.subscriber_headers)
        self.assertEqual(home.status_code, 200)
        self.assertTrue(home.json()["canReadPremium"])
        self.assertGreaterEqual(home.json()["availableDownloadCount"], 1)

    def _create_pdf_artifact(self) -> PublicationArtifact:
        draft = create_premium_research_draft(self.db, user_id=self.owner.id, source_payload=_source_payload())
        publication = self.db.get(ResearchPublication, draft["id"])
        version = self.db.get(PublicationVersion, draft["latestVersionId"])
        self._approve(publication, version)
        create_publication_snapshot(
            self.db,
            publication=publication,
            publication_version=version,
            user_id=self.owner.id,
        )
        snapshot = publication.snapshots[0]
        html_payload = render_publication_snapshot(self.db, snapshot=snapshot, user_id=self.owner.id)
        html_artifact = self.db.get(PublicationArtifact, html_payload["id"])
        pdf_payload = render_pdf_from_html_artifact(self.db, html_artifact=html_artifact, user_id=self.owner.id)
        return self.db.get(PublicationArtifact, pdf_payload["id"])

    def _approve(self, publication: ResearchPublication, version: PublicationVersion) -> None:
        review = PublicationReview(
            publication_id=publication.id,
            version_id=version.id,
            reviewer_user_id=self.owner.id,
            decision="approve",
            status="closed",
            comments="Revisao humana aprovada para entitlement.",
        )
        approval = PublicationApproval(
            publication_id=publication.id,
            version_id=version.id,
            approver_user_id=self.owner.id,
            decision="approve_publication",
            comments="Aprovacao final para entitlement.",
        )
        self.db.add_all([review, approval])
        publication.status = "approved"
        version.status = "approved"
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
