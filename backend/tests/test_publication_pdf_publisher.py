from __future__ import annotations

import unittest
from io import BytesIO

from pypdf import PdfReader
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
from app.premium_research.pdf_publisher import render_pdf_from_html_artifact
from app.premium_research.publisher import create_premium_research_draft
from app.premium_research.renderer import render_publication_snapshot
from app.premium_research.snapshot_engine import create_publication_snapshot
from tests.test_publication_snapshots import _source_payload


class PublicationPdfPublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="pdf-publisher@alpha.local", full_name="PDF User", password_hash="hash")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_pdf_artifact_is_binary_idempotent_and_readable(self) -> None:
        draft = create_premium_research_draft(self.db, user_id=self.user.id, source_payload=_source_payload())
        publication = self.db.get(ResearchPublication, draft["id"])
        version = self.db.get(PublicationVersion, draft["latestVersionId"])
        self._approve(publication, version)
        create_publication_snapshot(
            self.db,
            publication=publication,
            publication_version=version,
            user_id=self.user.id,
        )
        snapshot = publication.snapshots[0]
        html_payload = render_publication_snapshot(self.db, snapshot=snapshot, user_id=self.user.id)
        html_artifact = self.db.get(PublicationArtifact, html_payload["id"])

        first = render_pdf_from_html_artifact(self.db, html_artifact=html_artifact, user_id=self.user.id)
        second = render_pdf_from_html_artifact(self.db, html_artifact=html_artifact, user_id=self.user.id)
        rows = self.db.execute(select(PublicationArtifact)).scalars().all()
        pdf_artifact = self.db.get(PublicationArtifact, first["id"])
        reader = PdfReader(BytesIO(pdf_artifact.binary_content))

        self.assertEqual(len(rows), 2)
        self.assertEqual(first["artifactHash"], second["artifactHash"])
        self.assertTrue(second["alreadyExists"])
        self.assertEqual(pdf_artifact.artifact_type, "pdf")
        self.assertEqual(pdf_artifact.content_type, "application/pdf")
        self.assertEqual(pdf_artifact.source_artifact_id, html_artifact.id)
        self.assertTrue(pdf_artifact.binary_content.startswith(b"%PDF"))
        self.assertGreater(pdf_artifact.content_size_bytes, 1000)
        self.assertGreaterEqual(pdf_artifact.page_count, 1)
        self.assertEqual(pdf_artifact.page_count, len(reader.pages))
        self.assertIn("Carteira Alpha 360", reader.pages[0].extract_text())

    def _approve(self, publication: ResearchPublication, version: PublicationVersion) -> None:
        review = PublicationReview(
            publication_id=publication.id,
            version_id=version.id,
            reviewer_user_id=self.user.id,
            decision="approve",
            status="closed",
            comments="Revisao humana aprovada para PDF.",
        )
        approval = PublicationApproval(
            publication_id=publication.id,
            version_id=version.id,
            approver_user_id=self.user.id,
            decision="approve_publication",
            comments="Aprovacao final para PDF.",
        )
        self.db.add_all([review, approval])
        publication.status = "approved"
        version.status = "approved"
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
