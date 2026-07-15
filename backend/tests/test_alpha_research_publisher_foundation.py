from __future__ import annotations

from decimal import Decimal
import unittest

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    PublicationApproval,
    PublicationEvidence,
    PublicationReview,
    PublicationSection,
    PublicationSource,
    PublicationVersion,
    ResearchPublication,
    User,
)
from app.premium_research.contracts import (
    PublicationEvidenceContract,
    PublicationSectionContract,
    PublicationVersionContract,
    can_transition_publication,
    classify_publication_readiness,
    is_terminal_publication_status,
    to_dict,
)


class AlphaResearchPublisherFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_contract_status_transitions_are_explicit(self) -> None:
        self.assertTrue(can_transition_publication("created", "collecting_data"))
        self.assertFalse(can_transition_publication("created", "published"))
        self.assertTrue(can_transition_publication("published", "corrected"))
        self.assertTrue(is_terminal_publication_status("published"))
        self.assertFalse(is_terminal_publication_status("approved"))

    def test_readiness_classification_respects_blockers(self) -> None:
        self.assertEqual(classify_publication_readiness(95), "ready_for_publication")
        self.assertEqual(classify_publication_readiness(86), "ready_for_approval")
        self.assertEqual(classify_publication_readiness(72), "ready_for_review")
        self.assertEqual(classify_publication_readiness(45), "incomplete")
        self.assertEqual(classify_publication_readiness(95, has_blocker=True), "blocked")

    def test_contracts_serialize_to_api_ready_dicts(self) -> None:
        contract = PublicationVersionContract(
            version="v0.1",
            status="draft",
            readinessScore=82,
            readinessClassification="ready_for_approval",
            sections=[
                PublicationSectionContract(
                    key="market_context",
                    title="Contexto de mercado",
                    order=1,
                    status="draft",
                    confidence=88,
                    evidenceIds=["evidence-1"],
                )
            ],
            evidence=[
                PublicationEvidenceContract(
                    evidenceId="evidence-1",
                    domain="macro",
                    fieldName="selic",
                    sourceType="provider",
                    provider="bcb",
                    confidence=94,
                )
            ],
        )

        payload = to_dict(contract)

        self.assertEqual(payload["version"], "v0.1")
        self.assertEqual(payload["sections"][0]["key"], "market_context")
        self.assertEqual(payload["evidence"][0]["provider"], "bcb")

    def test_new_tables_are_additive_and_present_in_metadata(self) -> None:
        table_names = set(inspect(self.engine).get_table_names())

        self.assertIn("users", table_names)
        self.assertIn("assets", table_names)
        self.assertIn("research_publications", table_names)
        self.assertIn("publication_versions", table_names)
        self.assertIn("publication_sections", table_names)
        self.assertIn("publication_assets", table_names)
        self.assertIn("publication_sources", table_names)
        self.assertIn("publication_evidence", table_names)
        self.assertIn("publication_reviews", table_names)
        self.assertIn("publication_approvals", table_names)
        self.assertIn("publication_corrections", table_names)

    def test_publication_relationships_persist_without_touching_existing_payloads(self) -> None:
        user = User(email="publisher@alpha.local", full_name="Publisher User", password_hash="hash")
        publication = ResearchPublication(
            publication_type="monthly_research",
            period="2026-07",
            title="Alpha Premium Research - Julho 2026",
            status="draft",
            confidence=Decimal("91.50"),
        )
        self.db.add_all([user, publication])
        self.db.flush()

        version = PublicationVersion(
            publication_id=publication.id,
            version="v0.1",
            status="draft",
            readiness_score=Decimal("84.00"),
            readiness_classification="ready_for_approval",
            created_by_user_id=user.id,
        )
        self.db.add(version)
        self.db.flush()

        section = PublicationSection(
            publication_id=publication.id,
            version_id=version.id,
            section_key="portfolio_thesis",
            title="Tese da carteira",
            section_order=1,
            status="draft",
            content_markdown="Conteudo controlado por evidencia.",
            confidence=Decimal("88.00"),
        )
        source = PublicationSource(
            publication_id=publication.id,
            version_id=version.id,
            source_type="provider",
            provider="brapi",
            source_ref="quotes/BBSE3",
            title="Cotacao BBSE3",
            confidence=Decimal("94.00"),
        )
        self.db.add_all([section, source])
        self.db.flush()

        evidence = PublicationEvidence(
            publication_id=publication.id,
            version_id=version.id,
            section_id=section.id,
            evidence_key="bbse3.dividend_yield",
            domain="fundamentals",
            field_name="dividend_yield",
            source_type="provider",
            provider="brapi",
            confidence=Decimal("92.00"),
        )
        review = PublicationReview(
            publication_id=publication.id,
            version_id=version.id,
            reviewer_user_id=user.id,
            decision="approve",
            status="closed",
            comments="Aprovado para fluxo de publicacao.",
        )
        approval = PublicationApproval(
            publication_id=publication.id,
            version_id=version.id,
            approver_user_id=user.id,
            decision="approve_publication",
            comments="Aprovacao registrada.",
        )
        self.db.add_all([evidence, review, approval])
        self.db.commit()

        stored = self.db.get(ResearchPublication, publication.id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.period, "2026-07")
        self.assertEqual(len(stored.versions), 1)
        self.assertEqual(len(stored.sections), 1)
        self.assertEqual(len(stored.sources), 1)
        self.assertEqual(len(stored.evidence_links), 1)
        self.assertEqual(len(stored.reviews), 1)
        self.assertEqual(len(stored.approvals), 1)


if __name__ == "__main__":
    unittest.main()
