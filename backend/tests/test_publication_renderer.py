from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    PublicationApproval,
    PublicationArtifact,
    PublicationReview,
    PublicationVersion,
    ResearchPublication,
    User,
)
from app.premium_research.publisher import create_premium_research_draft
from app.premium_research.renderer import render_publication_snapshot
from app.premium_research.snapshot_engine import create_publication_snapshot
from tests.test_publication_snapshots import _source_payload


class PublicationRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="renderer@alpha.local", full_name="Renderer User", password_hash="hash")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_render_snapshot_creates_idempotent_html_artifact(self) -> None:
        draft = create_premium_research_draft(self.db, user_id=self.user.id, source_payload=_source_payload())
        publication = self.db.get(ResearchPublication, draft["id"])
        version = self.db.get(PublicationVersion, draft["latestVersionId"])
        self._approve(publication, version)
        snapshot_payload = create_publication_snapshot(
            self.db,
            publication=publication,
            publication_version=version,
            user_id=self.user.id,
        )
        snapshot = publication.snapshots[0]

        first = render_publication_snapshot(self.db, snapshot=snapshot, user_id=self.user.id)
        second = render_publication_snapshot(self.db, snapshot=snapshot, user_id=self.user.id)
        rows = self.db.execute(select(PublicationArtifact)).scalars().all()
        artifact = rows[0]

        self.assertEqual(len(rows), 1)
        self.assertTrue(first["artifactHash"])
        self.assertEqual(first["artifactHash"], second["artifactHash"])
        self.assertTrue(second["alreadyExists"])
        self.assertEqual(first["sourceSnapshotHash"], snapshot_payload["snapshotHash"])
        self.assertEqual(artifact.content_type, "text/html; charset=utf-8")
        self.assertIn("Carteira Alpha 360 Premium Research", artifact.html_content)
        self.assertIn(snapshot_payload["snapshotHash"], artifact.html_content)
        self.assertIn("BBSE3", artifact.html_content)
        self.assertGreater(len(artifact.evidence_ids_json), 2)

    def _approve(self, publication: ResearchPublication, version: PublicationVersion) -> None:
        review = PublicationReview(
            publication_id=publication.id,
            version_id=version.id,
            reviewer_user_id=self.user.id,
            decision="approve",
            status="closed",
            comments="Revisao humana aprovada para renderizacao.",
        )
        approval = PublicationApproval(
            publication_id=publication.id,
            version_id=version.id,
            approver_user_id=self.user.id,
            decision="approve_publication",
            comments="Aprovacao final para renderizacao.",
        )
        self.db.add_all([review, approval])
        publication.status = "approved"
        version.status = "approved"
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
