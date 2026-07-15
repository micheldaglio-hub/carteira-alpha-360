from __future__ import annotations

import json
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    AssetRating,
    AssetRatingVersion,
    AssetThesis,
    AssetThesisVersion,
    PublicationEvidence,
    PublicationSection,
    PublicationSource,
    PublicationVersion,
    ResearchCommitteeGateResult,
    ResearchCommitteeRun,
    ResearchCommitteeVote,
    ResearchPublication,
    User,
)
from app.premium_research.publisher import create_premium_research_draft


class AlphaResearchPublisherServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="premium@alpha.local", full_name="Premium User", password_hash="hash")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_create_premium_research_draft_persists_editorial_foundation(self) -> None:
        result = create_premium_research_draft(
            self.db,
            user_id=self.user.id,
            source_payload=_source_payload(),
        )

        publication = self.db.get(ResearchPublication, result["id"])
        versions = self.db.execute(select(PublicationVersion)).scalars().all()
        sections = self.db.execute(select(PublicationSection)).scalars().all()
        sources = self.db.execute(select(PublicationSource)).scalars().all()
        evidence = self.db.execute(select(PublicationEvidence)).scalars().all()
        theses = self.db.execute(select(AssetThesis)).scalars().all()
        thesis_versions = self.db.execute(select(AssetThesisVersion)).scalars().all()
        ratings = self.db.execute(select(AssetRating)).scalars().all()
        rating_versions = self.db.execute(select(AssetRatingVersion)).scalars().all()
        committee_runs = self.db.execute(select(ResearchCommitteeRun)).scalars().all()
        committee_gates = self.db.execute(select(ResearchCommitteeGateResult)).scalars().all()
        committee_votes = self.db.execute(select(ResearchCommitteeVote)).scalars().all()
        version_payload = json.loads(versions[0].payload_json)

        self.assertIsNotNone(publication)
        self.assertEqual(publication.period, "2026-07")
        self.assertEqual(publication.version, "v0.1")
        self.assertEqual(publication.status, "draft")
        self.assertEqual(len(versions), 1)
        self.assertGreaterEqual(len(sections), 5)
        self.assertGreaterEqual(len(sources), 6)
        self.assertGreaterEqual(len(evidence), 5)
        self.assertEqual(len(theses), 2)
        self.assertEqual(len(thesis_versions), 2)
        self.assertEqual(len(ratings), 2)
        self.assertEqual(len(rating_versions), 2)
        self.assertEqual(len(committee_runs), 1)
        self.assertEqual(len(committee_gates), 7)
        self.assertEqual(len(committee_votes), 5)
        self.assertEqual(version_payload["thesisSync"]["createdVersions"], 2)
        self.assertEqual(version_payload["ratingSync"]["createdVersions"], 2)
        self.assertIn(version_payload["researchCommittee"]["decision"], {"approved_for_review", "needs_review"})
        self.assertGreater(result["readiness"]["score"], 68)
        self.assertIn(result["readiness"]["classification"], {"ready_for_review", "ready_for_approval"})
        self.assertTrue(result["versionHash"])
        self.assertIn("revisao", publication.legal_disclaimer.lower())

    def test_second_draft_for_same_period_creates_next_version_without_overwriting(self) -> None:
        first = create_premium_research_draft(self.db, user_id=self.user.id, source_payload=_source_payload())
        second = create_premium_research_draft(self.db, user_id=self.user.id, source_payload=_source_payload())

        publications = self.db.execute(select(ResearchPublication).order_by(ResearchPublication.version)).scalars().all()

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual([item.version for item in publications], ["v0.1", "v0.2"])
        self.assertEqual(len(publications), 2)

    def test_low_evidence_draft_is_not_publishable(self) -> None:
        payload = _source_payload()
        payload["recommendedPortfolioReport"]["confidenceScore"] = 40
        payload["recommendedPortfolioReport"]["institutionalScore"] = 50
        payload["recommendationGovernance"]["dataConfidenceScore"] = 35
        payload["recommendationGovernance"]["blockers"] = ["Dados essenciais ainda insuficientes."]

        result = create_premium_research_draft(self.db, user_id=self.user.id, source_payload=payload)

        self.assertIn(result["status"], {"draft", "data_pending"})
        self.assertLess(result["readiness"]["score"], 82)
        self.assertNotEqual(result["readiness"]["classification"], "ready_for_publication")
        self.assertTrue(result["readiness"]["warnings"])


def _source_payload() -> dict:
    return {
        "methodology": [
            "Separar nucleo patrimonial, renda imobiliaria, global e cripto.",
            "Usar score, risco, fontes e governanca antes de qualquer publicacao.",
            "Historico ajuda a estudar o passado, mas nao promete resultado futuro.",
        ],
        "confidenceReport": {"overallScore": 83},
        "dataConfidenceAudit": {"overallScore": 78},
        "recommendationGovernance": {
            "confidenceScore": 83,
            "dataConfidenceScore": 78,
            "blockers": [],
            "plainLanguage": [
                "A carteira recomendada foi registrada com score institucional 84/100.",
                "A confianca do relatorio esta em 83/100.",
            ],
        },
        "recommendedPortfolioReport": {
            "id": "recommended-portfolio-alpha-2026-07",
            "reportMonth": "2026-07",
            "lastReviewDate": "2026-07-01",
            "nextReviewDate": "2026-08-01",
            "headline": "Carteira Recomendada Alpha em nivel institucional forte.",
            "executiveSummary": "Rascunho de estudo com foco em qualidade, renda e preservacao patrimonial.",
            "institutionalScore": 84,
            "confidenceScore": 83,
            "classification": "Institucional forte",
            "riskLevel": "moderado",
            "scoreBreakdown": {
                "corePortfolio": 82,
                "confidence": 83,
                "methodology": 92,
                "diversification": 88,
                "evidence": 80,
            },
            "evidenceLedger": [{"id": "e1"}, {"id": "e2"}],
            "assetReports": [
                {
                    "ticker": "BBSE3",
                    "name": "BB Seguridade",
                    "role": "Renda passiva",
                    "targetWeight": 15,
                    "institutionalScore": 86,
                    "classification": "Nucleo institucional",
                    "riskLevel": "moderado",
                    "monthlyReviewStatus": "acompanhar",
                    "evidence": ["ROE elevado", "Historico de proventos"],
                },
                {
                    "ticker": "TAEE11",
                    "name": "Taesa",
                    "role": "Previsibilidade de receita",
                    "targetWeight": 10,
                    "institutionalScore": 82,
                    "classification": "Alta confianca Alpha",
                    "riskLevel": "baixo_moderado",
                    "monthlyReviewStatus": "acompanhar",
                    "evidence": ["Contratos longos", "Historico de dividendos"],
                },
            ],
            "governanceLedgerV2": {
                "confidenceScore": 83,
                "dataConfidenceScore": 78,
                "blockers": [],
                "plainLanguage": [
                    "A carteira recomendada foi registrada com score institucional 84/100.",
                    "Cada revisao mensal preserva tese, evidencia e risco.",
                ],
            },
        },
    }


if __name__ == "__main__":
    unittest.main()
