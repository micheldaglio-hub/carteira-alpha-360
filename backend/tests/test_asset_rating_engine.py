from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Asset,
    AssetRating,
    AssetRatingEvidence,
    AssetRatingVersion,
    AssetThesisVersion,
    DataEvidenceLedger,
    User,
)
from app.premium_research.rating_engine import rate_thesis_version, sync_ratings_from_thesis_versions
from app.premium_research.thesis_engine import upsert_asset_thesis


class AssetRatingEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="rating@alpha.local", full_name="Rating User", password_hash="hash")
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

    def test_rate_thesis_version_creates_institutional_rating_with_evidence(self) -> None:
        thesis_version = self._create_thesis_version()

        result = rate_thesis_version(self.db, thesis_version, user_id=self.user.id)

        ratings = self.db.execute(select(AssetRating)).scalars().all()
        versions = self.db.execute(select(AssetRatingVersion)).scalars().all()
        links = self.db.execute(select(AssetRatingEvidence)).scalars().all()
        evidence = self.db.execute(select(DataEvidenceLedger).where(DataEvidenceLedger.domain == "rating")).scalars().all()

        self.assertTrue(result["createdVersion"])
        self.assertEqual(len(ratings), 1)
        self.assertEqual(len(versions), 1)
        self.assertEqual(len(links), 9)
        self.assertEqual(len(evidence), 9)
        self.assertEqual(ratings[0].ticker, "BBSE3")
        self.assertEqual(ratings[0].current_version, "v1")
        self.assertEqual(ratings[0].current_version_id, versions[0].id)
        self.assertGreater(float(versions[0].score_final), 70)
        self.assertTrue(versions[0].version_hash)
        self.assertEqual(versions[0].source_thesis_hash, thesis_version.version_hash)

    def test_same_thesis_version_does_not_duplicate_rating_version(self) -> None:
        thesis_version = self._create_thesis_version()
        first = rate_thesis_version(self.db, thesis_version, user_id=self.user.id)
        second = rate_thesis_version(self.db, thesis_version, user_id=self.user.id)

        versions = self.db.execute(select(AssetRatingVersion)).scalars().all()

        self.assertTrue(first["createdVersion"])
        self.assertFalse(second["createdVersion"])
        self.assertEqual(len(versions), 1)

    def test_new_thesis_version_creates_new_rating_version(self) -> None:
        first_thesis = self._create_thesis_version()
        rate_thesis_version(self.db, first_thesis, user_id=self.user.id)
        updated = _asset_report()
        updated["thesis"] = "Tese atualizada com maior cautela sobre ciclo de juros e qualidade de payout."
        upsert_asset_thesis(self.db, updated, user_id=self.user.id)
        second_thesis = self.db.execute(
            select(AssetThesisVersion).order_by(AssetThesisVersion.version.desc())
        ).scalars().first()

        result = rate_thesis_version(self.db, second_thesis, user_id=self.user.id)
        versions = self.db.execute(select(AssetRatingVersion).order_by(AssetRatingVersion.version)).scalars().all()
        rating = self.db.execute(select(AssetRating)).scalar_one()

        self.assertTrue(result["createdVersion"])
        self.assertEqual([row.version for row in versions], ["v1", "v2"])
        self.assertIsNotNone(versions[0].effective_to)
        self.assertIsNone(versions[1].effective_to)
        self.assertEqual(rating.current_version, "v2")

    def test_sync_rates_multiple_thesis_versions(self) -> None:
        bbse = self._create_thesis_version()
        taee_result = upsert_asset_thesis(self.db, _taee_report(), user_id=self.user.id)
        taee = self.db.get(AssetThesisVersion, taee_result["currentVersionId"])

        result = sync_ratings_from_thesis_versions(self.db, [bbse, taee], user_id=self.user.id)

        ratings = self.db.execute(select(AssetRating).order_by(AssetRating.ticker)).scalars().all()
        versions = self.db.execute(select(AssetRatingVersion)).scalars().all()

        self.assertEqual(result["assetCount"], 2)
        self.assertEqual(result["createdVersions"], 2)
        self.assertEqual([row.ticker for row in ratings], ["BBSE3", "TAEE11"])
        self.assertEqual(len(versions), 2)

    def _create_thesis_version(self) -> AssetThesisVersion:
        result = upsert_asset_thesis(self.db, _asset_report(), user_id=self.user.id)
        thesis_version = self.db.get(AssetThesisVersion, result["currentVersionId"])
        self.assertIsNotNone(thesis_version)
        return thesis_version


def _asset_report() -> dict:
    return {
        "ticker": "BBSE3",
        "name": "BB Seguridade",
        "assetClass": "Acoes",
        "role": "Renda passiva defensiva",
        "targetWeight": 15,
        "institutionalScore": 86,
        "confidenceScore": 84,
        "classification": "Nucleo institucional",
        "riskLevel": "moderado",
        "monthlyReviewStatus": "acompanhar",
        "dataQuality": "completos",
        "thesis": "Tese defensiva para renda passiva com seguradora de alta qualidade, geracao de caixa recorrente e governanca acompanhavel.",
        "evidence": ["ROE elevado", "Historico consistente de proventos"],
        "risks": ["Dependencia de juros e ciclo de credito"],
        "monitoring": ["Acompanhar sinistralidade, payout e regulacao"],
        "nextReviewDate": "2026-08-01",
    }


def _taee_report() -> dict:
    return {
        "ticker": "TAEE11",
        "name": "Taesa",
        "assetClass": "Acoes",
        "role": "Previsibilidade de receita",
        "targetWeight": 10,
        "institutionalScore": 82,
        "confidenceScore": 80,
        "classification": "Alta confianca Alpha",
        "riskLevel": "baixo_moderado",
        "monthlyReviewStatus": "acompanhar",
        "dataQuality": "completos",
        "thesis": "Tese de previsibilidade de receita com contratos regulados, caixa monitorado e historico de distribuicao.",
        "evidence": ["Contratos longos", "Historico de proventos"],
        "risks": ["Revisao regulatoria"],
        "monitoring": ["Monitorar regulacao e alavancagem"],
        "nextReviewDate": "2026-08-01",
    }


if __name__ == "__main__":
    unittest.main()
