from __future__ import annotations

import json
import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.core.config import get_settings
from app.database import Base, get_db
from app.distribution.engine import create_distribution_campaign, dispatch_distribution_campaign
from app.main import app
from app.models import (
    DistributionCampaign,
    DistributionEventLog,
    DistributionRecipient,
    PublicationApproval,
    PublicationArtifact,
    PublicationReview,
    PublicationVersion,
    ResearchPublication,
    User,
)
from app.premium_research.entitlements import grant_subscription_to_user
from app.premium_research.pdf_publisher import render_pdf_from_html_artifact
from app.premium_research.publisher import create_premium_research_draft
from app.premium_research.renderer import render_publication_snapshot
from app.premium_research.snapshot_engine import create_publication_snapshot
from app.services.rbac import grant_role_to_user
from tests.test_publication_snapshots import _source_payload


class DistributionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.owner = User(email="distribution-owner@alpha.local", full_name="Distribution Owner", password_hash="hash")
        self.subscriber = User(email="distribution-subscriber@alpha.local", full_name="Distribution Subscriber", password_hash="hash")
        self.db.add_all([self.owner, self.subscriber])
        self.db.commit()
        grant_role_to_user(self.db, user_id=self.owner.id, role="admin", source="test", commit=True)
        grant_role_to_user(self.db, user_id=self.subscriber.id, role="free_user", source="test", commit=True)
        grant_subscription_to_user(
            self.db,
            user_id=self.subscriber.id,
            plan_code="alpha_premium",
            period_days=30,
            billing_provider="test",
            commit=True,
        )

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

    def test_campaign_and_mock_dispatch_to_premium_subscriber(self) -> None:
        pdf_artifact = self._create_pdf_artifact()
        created = create_distribution_campaign(
            self.db,
            publication_id=pdf_artifact.publication_id,
            artifact_id=pdf_artifact.id,
            created_by_user_id=self.owner.id,
            audience_type="premium_subscribers",
            subject="Edicao premium Alpha",
            commit=True,
        )
        dispatched = dispatch_distribution_campaign(
            self.db,
            campaign_id=created["id"],
            actor_user_id=self.owner.id,
            commit=True,
        )

        campaigns = self.db.execute(select(DistributionCampaign)).scalars().all()
        recipients = self.db.execute(select(DistributionRecipient)).scalars().all()
        events = self.db.execute(select(DistributionEventLog)).scalars().all()

        self.assertEqual(len(campaigns), 1)
        self.assertEqual(created["recipientCount"], 1)
        self.assertEqual(dispatched["status"], "sent")
        self.assertEqual(dispatched["deliveredCount"], 1)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].email, self.subscriber.email)
        self.assertEqual(recipients[0].status, "delivered")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "delivered")
        event_payload = json.loads(events[0].payload_json)
        self.assertEqual(event_payload["provider"], "mock")
        self.assertEqual(event_payload["mode"], "mock")
        self.assertIn("subject", event_payload)

    def test_distribution_api_create_and_dispatch(self) -> None:
        pdf_artifact = self._create_pdf_artifact()
        created = self.client.post(
            "/api/distribution/campaigns",
            json={
                "publication_id": pdf_artifact.publication_id,
                "artifact_id": pdf_artifact.id,
                "audience_type": "premium_subscribers",
                "subject": "Alpha Premium via API",
            },
            headers=self.owner_headers,
        )
        self.assertEqual(created.status_code, 201)
        campaign_id = created.json()["id"]

        dispatched = self.client.post(f"/api/distribution/campaigns/{campaign_id}/dispatch", headers=self.owner_headers)
        detail = self.client.get(f"/api/distribution/campaigns/{campaign_id}?include_events=true", headers=self.owner_headers)
        listing = self.client.get("/api/distribution/campaigns", headers=self.owner_headers)

        self.assertEqual(dispatched.status_code, 200)
        self.assertEqual(dispatched.json()["deliveredCount"], 1)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.json()["recipients"]), 1)
        self.assertEqual(len(detail.json()["events"]), 1)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["count"], 1)

    def test_subscriber_delivery_inbox_tracks_delivery_and_download(self) -> None:
        pdf_artifact = self._create_pdf_artifact()
        created = create_distribution_campaign(
            self.db,
            publication_id=pdf_artifact.publication_id,
            artifact_id=pdf_artifact.id,
            created_by_user_id=self.owner.id,
            audience_type="premium_subscribers",
            subject="Inbox Alpha Premium",
            commit=True,
        )
        dispatch_distribution_campaign(
            self.db,
            campaign_id=created["id"],
            actor_user_id=self.owner.id,
            commit=True,
        )

        inbox = self.client.get("/api/premium/subscriber/delivery-inbox", headers=self.subscriber_headers)
        home = self.client.get("/api/premium/subscriber/home", headers=self.subscriber_headers)

        self.assertEqual(inbox.status_code, 200)
        self.assertEqual(inbox.json()["summary"]["received"], 1)
        self.assertEqual(inbox.json()["summary"]["downloaded"], 0)
        self.assertEqual(home.status_code, 200)
        self.assertEqual(home.json()["deliveryInbox"]["summary"]["received"], 1)

        downloaded = self.client.get(
            f"/api/premium/artifacts/{pdf_artifact.id}/download",
            headers=self.subscriber_headers,
        )
        inbox_after_download = self.client.get("/api/premium/subscriber/delivery-inbox", headers=self.subscriber_headers)

        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(inbox_after_download.status_code, 200)
        self.assertEqual(inbox_after_download.json()["summary"]["downloaded"], 1)
        self.assertTrue(inbox_after_download.json()["items"][0]["downloaded"])

    def test_resend_without_key_falls_back_to_mock_provider(self) -> None:
        previous_provider = os.environ.get("DISTRIBUTION_PROVIDER")
        previous_resend_key = os.environ.get("DISTRIBUTION_RESEND_API_KEY")
        os.environ["DISTRIBUTION_PROVIDER"] = "resend"
        os.environ.pop("DISTRIBUTION_RESEND_API_KEY", None)
        get_settings.cache_clear()
        try:
            pdf_artifact = self._create_pdf_artifact()
            created = create_distribution_campaign(
                self.db,
                publication_id=pdf_artifact.publication_id,
                artifact_id=pdf_artifact.id,
                created_by_user_id=self.owner.id,
                audience_type="premium_subscribers",
                subject="Fallback Resend",
                commit=True,
            )
        finally:
            if previous_provider is None:
                os.environ.pop("DISTRIBUTION_PROVIDER", None)
            else:
                os.environ["DISTRIBUTION_PROVIDER"] = previous_provider
            if previous_resend_key is None:
                os.environ.pop("DISTRIBUTION_RESEND_API_KEY", None)
            else:
                os.environ["DISTRIBUTION_RESEND_API_KEY"] = previous_resend_key
            get_settings.cache_clear()

        self.assertEqual(created["provider"], "mock")
        self.assertEqual(created["metadata"]["configuredProvider"], "resend")
        self.assertIn("DISTRIBUTION_RESEND_API_KEY", created["metadata"]["fallbackReason"])

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
            comments="Revisao humana aprovada para distribuicao.",
        )
        approval = PublicationApproval(
            publication_id=publication.id,
            version_id=version.id,
            approver_user_id=self.owner.id,
            decision="approve_publication",
            comments="Aprovacao final para distribuicao.",
        )
        self.db.add_all([review, approval])
        publication.status = "approved"
        version.status = "approved"
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
