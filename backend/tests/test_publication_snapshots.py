from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    PublicationApproval,
    PublicationReview,
    PublicationSnapshot,
    PublicationVersion,
    ResearchPublication,
    User,
)
from app.premium_research.publisher import create_premium_research_draft
from app.premium_research.snapshot_engine import (
    PublicationSnapshotError,
    create_publication_snapshot,
    snapshot_to_dict,
)


class PublicationSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="snapshot@alpha.local", full_name="Snapshot User", password_hash="hash")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_snapshot_requires_human_approval_by_default(self) -> None:
        result = create_premium_research_draft(self.db, user_id=self.user.id, source_payload=_source_payload())
        publication = self.db.get(ResearchPublication, result["id"])
        version = self.db.get(PublicationVersion, result["latestVersionId"])

        with self.assertRaises(PublicationSnapshotError):
            create_publication_snapshot(
                self.db,
                publication=publication,
                publication_version=version,
                user_id=self.user.id,
            )

    def test_approved_snapshot_is_immutable_idempotent_and_hash_verified(self) -> None:
        result = create_premium_research_draft(self.db, user_id=self.user.id, source_payload=_source_payload())
        publication = self.db.get(ResearchPublication, result["id"])
        version = self.db.get(PublicationVersion, result["latestVersionId"])
        self._approve(publication, version)

        first = create_publication_snapshot(
            self.db,
            publication=publication,
            publication_version=version,
            user_id=self.user.id,
        )
        second = create_publication_snapshot(
            self.db,
            publication=publication,
            publication_version=version,
            user_id=self.user.id,
        )
        rows = self.db.execute(select(PublicationSnapshot)).scalars().all()
        snapshot = self.db.get(PublicationSnapshot, first["id"])
        detail = snapshot_to_dict(snapshot, include_payload=True)

        self.assertEqual(len(rows), 1)
        self.assertTrue(first["snapshotHash"])
        self.assertEqual(first["snapshotHash"], second["snapshotHash"])
        self.assertTrue(second["alreadyExists"])
        self.assertTrue(first["isImmutable"])
        self.assertEqual(detail["integrity"]["status"], "ok")
        self.assertEqual(detail["sectionCount"], 5)
        self.assertEqual(detail["assetCount"], 2)
        self.assertIn("payload", detail)

    def _approve(self, publication: ResearchPublication, version: PublicationVersion) -> None:
        review = PublicationReview(
            publication_id=publication.id,
            version_id=version.id,
            reviewer_user_id=self.user.id,
            decision="approve",
            status="closed",
            comments="Revisao humana aprovada para snapshot.",
        )
        approval = PublicationApproval(
            publication_id=publication.id,
            version_id=version.id,
            approver_user_id=self.user.id,
            decision="approve_publication",
            comments="Aprovacao final para snapshot.",
        )
        self.db.add_all([review, approval])
        publication.status = "approved"
        version.status = "approved"
        self.db.commit()


def _source_payload() -> dict:
    return {
        "methodology": [
            "Separar nucleo patrimonial, renda imobiliaria, global e cripto.",
            "Usar score, risco, fontes e governanca antes de qualquer publicacao.",
            "Historico ajuda a estudar o passado, mas nao promete resultado futuro.",
        ],
        "confidenceReport": {"overallScore": 84},
        "dataConfidenceAudit": {"overallScore": 81},
        "recommendationGovernance": {
            "confidenceScore": 84,
            "dataConfidenceScore": 81,
            "blockers": [],
            "plainLanguage": [
                "A carteira recomendada foi registrada com score institucional forte.",
                "A confianca do relatorio esta em nivel bom.",
            ],
        },
        "recommendedPortfolioReport": {
            "id": "recommended-portfolio-alpha-2026-07",
            "reportMonth": "2026-07",
            "lastReviewDate": "2026-07-01",
            "nextReviewDate": "2026-08-01",
            "headline": "Carteira Recomendada Alpha em nivel institucional forte.",
            "executiveSummary": "Rascunho de estudo com foco em qualidade, renda e preservacao patrimonial.",
            "institutionalScore": 85,
            "confidenceScore": 84,
            "classification": "Institucional forte",
            "riskLevel": "moderado",
            "scoreBreakdown": {
                "corePortfolio": 82,
                "confidence": 84,
                "methodology": 92,
                "diversification": 88,
                "evidence": 82,
            },
            "evidenceLedger": [{"id": "e1"}, {"id": "e2"}],
            "assetReports": [
                {
                    "ticker": "BBSE3",
                    "name": "BB Seguridade",
                    "role": "Renda passiva",
                    "targetWeight": 15,
                    "institutionalScore": 86,
                    "confidenceScore": 85,
                    "classification": "Nucleo institucional",
                    "riskLevel": "moderado",
                    "monthlyReviewStatus": "acompanhar",
                    "dataQuality": "completos",
                    "thesis": "Tese defensiva para renda passiva com caixa recorrente e historico de distribuicao.",
                    "evidence": ["ROE elevado", "Historico consistente de proventos"],
                    "risks": ["Ciclo de credito e regulacao setorial"],
                    "monitoring": ["Acompanhar payout e mudancas regulatorias"],
                },
                {
                    "ticker": "TAEE11",
                    "name": "Taesa",
                    "role": "Previsibilidade de receita",
                    "targetWeight": 10,
                    "institutionalScore": 82,
                    "confidenceScore": 83,
                    "classification": "Alta confianca Alpha",
                    "riskLevel": "baixo_moderado",
                    "monthlyReviewStatus": "acompanhar",
                    "dataQuality": "completos",
                    "thesis": "Tese de previsibilidade com contratos longos e historico de distribuicao.",
                    "evidence": ["Contratos longos", "Historico de dividendos"],
                    "risks": ["Revisoes regulatórias e custo de capital"],
                    "monitoring": ["Acompanhar RAP, alavancagem e renovacoes"],
                },
            ],
            "governanceLedgerV2": {
                "confidenceScore": 84,
                "dataConfidenceScore": 81,
                "blockers": [],
                "plainLanguage": [
                    "A carteira recomendada foi registrada com score institucional forte.",
                    "Cada revisao mensal preserva tese, evidencia e risco.",
                ],
            },
        },
    }


if __name__ == "__main__":
    unittest.main()
