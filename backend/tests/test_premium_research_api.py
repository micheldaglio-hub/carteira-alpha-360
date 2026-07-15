from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.services.rbac import grant_role_to_user


class PremiumResearchApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="premium-api@alpha.local", full_name="Premium API User", password_hash="hash")
        self.db.add(self.user)
        self.db.commit()
        grant_role_to_user(self.db, user_id=self.user.id, role="admin", source="test", commit=True)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        token = create_access_token(self.user.id)
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_premium_routes_require_authentication(self) -> None:
        response = self.client.get("/api/premium/publications")

        self.assertEqual(response.status_code, 401)

    def test_create_draft_and_inspect_admin_workflow(self) -> None:
        created = self.client.post(
            "/api/premium/publications/drafts",
            json={"period": "2026-07", "title": "Alpha Premium Test"},
            headers=self.headers,
        )

        self.assertEqual(created.status_code, 201)
        publication = created.json()
        publication_id = publication["id"]
        version_id = publication["latestVersionId"]

        self.assertEqual(publication["period"], "2026-07")
        self.assertTrue(version_id)
        self.assertGreaterEqual(publication["sectionCount"], 5)

        listing = self.client.get("/api/premium/publications", headers=self.headers).json()
        detail = self.client.get(f"/api/premium/publications/{publication_id}", headers=self.headers).json()
        version = self.client.get(
            f"/api/premium/publications/{publication_id}/versions/{version_id}",
            headers=self.headers,
        ).json()
        theses = self.client.get("/api/premium/theses", headers=self.headers).json()
        ratings = self.client.get("/api/premium/ratings", headers=self.headers).json()
        committee_runs = self.client.get("/api/premium/committee/runs", headers=self.headers).json()

        self.assertEqual(listing["count"], 1)
        self.assertEqual(detail["id"], publication_id)
        self.assertEqual(version["id"], version_id)
        self.assertIn("researchCommittee", version["payload"])
        self.assertGreater(theses["count"], 0)
        self.assertGreater(ratings["count"], 0)
        self.assertEqual(committee_runs["count"], 1)

        committee = self.client.post(
            f"/api/premium/publications/{publication_id}/committee/run",
            json={"publication_version_id": version_id},
            headers=self.headers,
        ).json()

        self.assertIn(committee["decision"], {"approved_for_review", "needs_review", "request_changes", "blocked"})
        self.assertEqual(committee["publicationId"], publication_id)
        self.assertEqual(committee["publicationVersionId"], version_id)

        attribution = self.client.post(
            f"/api/premium/publications/{publication_id}/attribution/run",
            json={
                "publication_version_id": version_id,
                "benchmark_name": "Benchmark Teste",
                "benchmark_return_pct": 1.0,
                "refresh_market": False,
            },
            headers=self.headers,
        )
        self.assertEqual(attribution.status_code, 201)
        attribution_payload = attribution.json()
        self.assertEqual(attribution_payload["publicationId"], publication_id)
        self.assertEqual(attribution_payload["publicationVersionId"], version_id)
        self.assertIn("portfolioReturnPct", attribution_payload)
        self.assertIn("assetRows", attribution_payload)
        self.assertGreater(len(attribution_payload["assetRows"]), 0)

        attribution_runs = self.client.get("/api/premium/attribution/runs", headers=self.headers).json()
        self.assertEqual(attribution_runs["count"], 1)
        attribution_detail = self.client.get(
            f"/api/premium/attribution/runs/{attribution_payload['id']}",
            headers=self.headers,
        ).json()
        self.assertEqual(attribution_detail["id"], attribution_payload["id"])
        self.assertGreater(len(attribution_detail["assetRows"]), 0)

        premature_snapshot = self.client.post(
            f"/api/premium/publications/{publication_id}/snapshots",
            json={"publication_version_id": version_id},
            headers=self.headers,
        )
        self.assertEqual(premature_snapshot.status_code, 409)

        premature_approval = self.client.post(
            f"/api/premium/publications/{publication_id}/approvals",
            json={"publication_version_id": version_id, "decision": "approve_publication"},
            headers=self.headers,
        )
        self.assertEqual(premature_approval.status_code, 409)

        review = self.client.post(
            f"/api/premium/publications/{publication_id}/reviews",
            json={
                "publication_version_id": version_id,
                "decision": "approve",
                "comments": "Revisao humana aprovada para teste.",
            },
            headers=self.headers,
        )
        self.assertEqual(review.status_code, 201)
        self.assertEqual(review.json()["review"]["decision"], "approve")
        self.assertEqual(review.json()["publication"]["status"], "reviewed")

        approval = self.client.post(
            f"/api/premium/publications/{publication_id}/approvals",
            json={
                "publication_version_id": version_id,
                "decision": "approve_publication",
                "comments": "Aprovacao final registrada para teste.",
            },
            headers=self.headers,
        )
        if committee["decision"] == "blocked" or committee["blockerCount"] > 0:
            self.assertEqual(approval.status_code, 409)
        else:
            self.assertEqual(approval.status_code, 201)
            self.assertEqual(approval.json()["approval"]["decision"], "approve_publication")
            self.assertEqual(approval.json()["publication"]["status"], "approved")
            snapshot = self.client.post(
                f"/api/premium/publications/{publication_id}/snapshots",
                json={"publication_version_id": version_id, "include_payload": True},
                headers=self.headers,
            )
            self.assertEqual(snapshot.status_code, 201)
            snapshot_payload = snapshot.json()
            self.assertEqual(snapshot_payload["publicationId"], publication_id)
            self.assertEqual(snapshot_payload["publicationVersionId"], version_id)
            self.assertEqual(snapshot_payload["integrity"]["status"], "ok")
            self.assertTrue(snapshot_payload["snapshotHash"])
            self.assertIn("payload", snapshot_payload)

            artifact = self.client.post(
                f"/api/premium/snapshots/{snapshot_payload['id']}/render",
                json={"artifact_type": "html", "include_content": True},
                headers=self.headers,
            )
            self.assertEqual(artifact.status_code, 201)
            artifact_payload = artifact.json()
            self.assertEqual(artifact_payload["snapshotId"], snapshot_payload["id"])
            self.assertEqual(artifact_payload["sourceSnapshotHash"], snapshot_payload["snapshotHash"])
            self.assertTrue(artifact_payload["artifactHash"])
            self.assertIn("htmlContent", artifact_payload)
            self.assertIn("Carteira Alpha 360 Premium Research", artifact_payload["htmlContent"])

            artifact_again = self.client.post(
                f"/api/premium/snapshots/{snapshot_payload['id']}/render",
                json={"artifact_type": "html"},
                headers=self.headers,
            )
            self.assertEqual(artifact_again.status_code, 201)
            self.assertTrue(artifact_again.json()["alreadyExists"])

            pdf_artifact = self.client.post(
                f"/api/premium/artifacts/{artifact_payload['id']}/pdf",
                json={"force": False},
                headers=self.headers,
            )
            self.assertEqual(pdf_artifact.status_code, 201)
            pdf_payload = pdf_artifact.json()
            self.assertEqual(pdf_payload["artifactType"], "pdf")
            self.assertEqual(pdf_payload["sourceArtifactId"], artifact_payload["id"])
            self.assertEqual(pdf_payload["contentType"], "application/pdf")
            self.assertGreater(pdf_payload["contentSizeBytes"], 1000)
            self.assertGreaterEqual(pdf_payload["pageCount"], 1)
            self.assertIn("downloadUrl", pdf_payload)

            pdf_again = self.client.post(
                f"/api/premium/artifacts/{artifact_payload['id']}/pdf",
                json={"force": False},
                headers=self.headers,
            )
            self.assertEqual(pdf_again.status_code, 201)
            self.assertTrue(pdf_again.json()["alreadyExists"])

            downloaded = self.client.get(
                f"/api/premium/artifacts/{pdf_payload['id']}/download",
                headers=self.headers,
            )
            self.assertEqual(downloaded.status_code, 200)
            self.assertEqual(downloaded.headers["content-type"], "application/pdf")
            self.assertTrue(downloaded.content.startswith(b"%PDF"))

            artifacts = self.client.get("/api/premium/artifacts", headers=self.headers).json()
            self.assertEqual(artifacts["count"], 2)
            artifact_detail = self.client.get(
                f"/api/premium/artifacts/{artifact_payload['id']}",
                headers=self.headers,
            ).json()
            self.assertEqual(artifact_detail["artifactHash"], artifact_payload["artifactHash"])
            publication_artifacts = self.client.get(
                f"/api/premium/publications/{publication_id}/artifacts",
                headers=self.headers,
            ).json()
            self.assertEqual(publication_artifacts["count"], 2)

            snapshot_again = self.client.post(
                f"/api/premium/publications/{publication_id}/snapshots",
                json={"publication_version_id": version_id},
                headers=self.headers,
            )
            self.assertEqual(snapshot_again.status_code, 201)
            self.assertTrue(snapshot_again.json()["alreadyExists"])

            snapshots = self.client.get("/api/premium/snapshots", headers=self.headers).json()
            self.assertEqual(snapshots["count"], 1)

        rejection = self.client.post(
            f"/api/premium/publications/{publication_id}/approvals",
            json={
                "publication_version_id": version_id,
                "decision": "reject_publication",
                "comments": "Rejeicao editorial registrada para teste.",
            },
            headers=self.headers,
        )
        self.assertEqual(rejection.status_code, 201)
        self.assertEqual(rejection.json()["approval"]["decision"], "reject_publication")


if __name__ == "__main__":
    unittest.main()
