from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Asset,
    AssetRatingVersion,
    AssetThesisVersion,
    PublicationVersion,
    ResearchCommitteeGateResult,
    ResearchCommitteeRun,
    ResearchCommitteeVote,
    ResearchPublication,
    User,
)
from app.premium_research.rating_engine import rate_thesis_version
from app.premium_research.research_committee import run_research_committee, run_research_committee_for_publication
from app.premium_research.thesis_engine import upsert_asset_thesis


class ResearchCommitteeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="committee@alpha.local", full_name="Committee User", password_hash="hash")
        self.asset = Asset(
            ticker="BBSE3",
            name="BB Seguridade",
            asset_class="Acoes",
            sector="Seguros",
            universal_symbol="BR:BBSE3",
        )
        self.db.add_all([self.user, self.asset])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_committee_approves_strong_research_for_human_review_only(self) -> None:
        publication, version = self._publication()
        thesis_version = self._create_thesis_version(publication, version, _strong_report())
        rate_thesis_version(
            self.db,
            thesis_version,
            publication=publication,
            publication_version=version,
            user_id=self.user.id,
        )

        result = run_research_committee_for_publication(
            self.db,
            publication=publication,
            publication_version=version,
            user_id=self.user.id,
        )

        runs = self.db.execute(select(ResearchCommitteeRun)).scalars().all()
        gates = self.db.execute(select(ResearchCommitteeGateResult)).scalars().all()
        votes = self.db.execute(select(ResearchCommitteeVote)).scalars().all()

        self.assertEqual(len(runs), 1)
        self.assertEqual(result["decision"], "approved_for_review")
        self.assertGreaterEqual(result["approvalScore"], 75)
        self.assertEqual(result["blockerCount"], 0)
        self.assertEqual(len(gates), 7)
        self.assertEqual(len(votes), 5)
        self.assertIn("nao publica", result["summary"])

    def test_committee_blocks_publication_without_rating_gate(self) -> None:
        publication, version = self._publication()
        self._create_thesis_version(publication, version, _strong_report())

        result = run_research_committee_for_publication(
            self.db,
            publication=publication,
            publication_version=version,
            user_id=self.user.id,
        )

        self.assertEqual(result["decision"], "blocked")
        self.assertGreater(result["blockerCount"], 0)
        self.assertTrue(any(gate["key"] == "rating_coverage" and gate["status"] == "block" for gate in result["gates"]))

    def test_committee_blocks_restricted_high_risk_rating(self) -> None:
        publication, version = self._publication()
        thesis_version = self._create_thesis_version(publication, version, _restricted_report())
        rating_result = rate_thesis_version(
            self.db,
            thesis_version,
            publication=publication,
            publication_version=version,
            user_id=self.user.id,
        )
        rating_version = self.db.get(AssetRatingVersion, rating_result["currentVersionId"])

        result = run_research_committee(
            self.db,
            publication=publication,
            publication_version=version,
            thesis_versions=[thesis_version],
            rating_versions=[rating_version],
            user_id=self.user.id,
        )

        self.assertEqual(result["decision"], "blocked")
        self.assertTrue(any(gate["key"] == "guardian_risk" and gate["status"] == "block" for gate in result["gates"]))
        self.assertTrue(result["blockers"])

    def _publication(self) -> tuple[ResearchPublication, PublicationVersion]:
        publication = ResearchPublication(
            publication_type="monthly_research",
            period="2026-07",
            title="Research Committee Test",
            status="processing",
            version="v0.1",
            author_user_id=self.user.id,
            legal_disclaimer="Conteudo analitico para revisao humana; nao representa ordem automatica.",
        )
        self.db.add(publication)
        self.db.flush()
        version = PublicationVersion(
            publication_id=publication.id,
            version="v0.1",
            status="draft",
            readiness_score=82,
            readiness_classification="ready_for_approval",
            created_by_user_id=self.user.id,
        )
        self.db.add(version)
        self.db.commit()
        return publication, version

    def _create_thesis_version(
        self,
        publication: ResearchPublication,
        version: PublicationVersion,
        report: dict,
    ) -> AssetThesisVersion:
        result = upsert_asset_thesis(
            self.db,
            report,
            publication=publication,
            publication_version=version,
            user_id=self.user.id,
        )
        thesis_version = self.db.get(AssetThesisVersion, result["currentVersionId"])
        self.assertIsNotNone(thesis_version)
        return thesis_version


def _strong_report() -> dict:
    return {
        "ticker": "BBSE3",
        "name": "BB Seguridade",
        "assetClass": "Acoes",
        "role": "Renda passiva defensiva",
        "targetWeight": 15,
        "institutionalScore": 88,
        "confidenceScore": 86,
        "classification": "Nucleo institucional",
        "riskLevel": "moderado",
        "monthlyReviewStatus": "acompanhar",
        "dataQuality": "completos",
        "thesis": "Tese defensiva para renda passiva com caixa recorrente, historico de distribuicao, governanca acompanhavel e papel claro no nucleo patrimonial.",
        "evidence": ["ROE elevado", "Historico consistente de proventos", "Modelo de negocio resiliente"],
        "risks": ["Dependencia de juros, ciclo de credito e regulacao setorial"],
        "monitoring": ["Acompanhar sinistralidade, payout, margem financeira e mudancas regulatorias"],
        "nextReviewDate": "2026-08-01",
    }


def _restricted_report() -> dict:
    return {
        "ticker": "RISK3",
        "name": "Ativo de Risco",
        "assetClass": "Acoes",
        "role": "Especulativo",
        "targetWeight": 40,
        "institutionalScore": 18,
        "confidenceScore": 30,
        "classification": "Fora dos criterios",
        "riskLevel": "extremo",
        "monthlyReviewStatus": "revalidar",
        "dataQuality": "fallback",
        "thesis": "Tese curta e insuficiente.",
        "evidence": [],
        "risks": ["Risco extremo e dados insuficientes"],
        "monitoring": [],
        "nextReviewDate": "2026-08-01",
    }


if __name__ == "__main__":
    unittest.main()
