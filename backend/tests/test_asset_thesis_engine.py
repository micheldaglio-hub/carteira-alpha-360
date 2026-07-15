from __future__ import annotations

import unittest

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from app.database import Base
from app.models import Asset, AssetThesis, AssetThesisEvidence, AssetThesisVersion, DataEvidenceLedger, User
from app.premium_research.thesis_engine import sync_theses_from_recommended_report, upsert_asset_thesis


class AssetThesisEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="thesis@alpha.local", full_name="Thesis User", password_hash="hash")
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

    def test_upsert_creates_versioned_thesis_with_evidence(self) -> None:
        result = upsert_asset_thesis(self.db, _asset_report(), user_id=self.user.id)

        theses = self.db.execute(select(AssetThesis)).scalars().all()
        versions = self.db.execute(select(AssetThesisVersion)).scalars().all()
        links = self.db.execute(select(AssetThesisEvidence)).scalars().all()
        evidence = self.db.execute(select(DataEvidenceLedger)).scalars().all()

        self.assertTrue(result["createdVersion"])
        self.assertEqual(len(theses), 1)
        self.assertEqual(len(versions), 1)
        self.assertEqual(len(links), 6)
        self.assertEqual(len(evidence), 6)
        self.assertEqual(theses[0].ticker, "BBSE3")
        self.assertEqual(theses[0].current_version, "v1")
        self.assertEqual(theses[0].current_version_id, versions[0].id)
        self.assertEqual(versions[0].thesis_text, "Tese defensiva para renda passiva com seguradora de alta qualidade.")
        self.assertTrue(versions[0].version_hash)

    def test_unchanged_report_does_not_create_duplicate_version(self) -> None:
        first = upsert_asset_thesis(self.db, _asset_report(), user_id=self.user.id)
        second = upsert_asset_thesis(self.db, _asset_report(), user_id=self.user.id)

        versions = self.db.execute(select(AssetThesisVersion)).scalars().all()

        self.assertTrue(first["createdVersion"])
        self.assertFalse(second["createdVersion"])
        self.assertEqual(len(versions), 1)

    def test_changed_report_creates_new_version_and_closes_previous(self) -> None:
        upsert_asset_thesis(self.db, _asset_report(), user_id=self.user.id)
        updated_report = _asset_report()
        updated_report["thesis"] = "Tese atualizada com foco maior em qualidade de caixa e disciplina de payout."

        result = upsert_asset_thesis(
            self.db,
            updated_report,
            user_id=self.user.id,
            change_reason="Revisao mensal alterou a leitura da tese.",
        )
        versions = self.db.execute(select(AssetThesisVersion).order_by(AssetThesisVersion.version)).scalars().all()
        thesis = self.db.execute(select(AssetThesis)).scalar_one()

        self.assertTrue(result["createdVersion"])
        self.assertEqual([row.version for row in versions], ["v1", "v2"])
        self.assertIsNotNone(versions[0].effective_to)
        self.assertIsNone(versions[1].effective_to)
        self.assertEqual(thesis.current_version, "v2")
        self.assertEqual(thesis.current_version_id, versions[1].id)

    def test_sync_from_recommended_report_versions_all_assets(self) -> None:
        report = {
            "id": "recommended-portfolio-alpha-2026-07",
            "assetReports": [
                _asset_report(),
                {
                    "ticker": "TAEE11",
                    "name": "Taesa",
                    "assetClass": "Acoes",
                    "role": "Previsibilidade de receita",
                    "targetWeight": 10,
                    "institutionalScore": 82,
                    "confidenceScore": 80,
                    "riskLevel": "baixo_moderado",
                    "monthlyReviewStatus": "acompanhar",
                    "thesis": "Tese de previsibilidade de receita com contratos regulados.",
                    "evidence": ["Contratos longos", "Historico de proventos"],
                    "risks": ["Revisao regulatoria"],
                    "monitoring": ["Monitorar regulacao e alavancagem"],
                    "nextReviewDate": "2026-08-01",
                },
            ],
        }

        result = sync_theses_from_recommended_report(self.db, report, user_id=self.user.id)

        theses = self.db.execute(select(AssetThesis).order_by(AssetThesis.ticker)).scalars().all()
        versions = self.db.execute(select(AssetThesisVersion)).scalars().all()

        self.assertEqual(result["assetCount"], 2)
        self.assertEqual(result["createdVersions"], 2)
        self.assertEqual([row.ticker for row in theses], ["BBSE3", "TAEE11"])
        self.assertEqual(len(versions), 2)


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
        "thesis": "Tese defensiva para renda passiva com seguradora de alta qualidade.",
        "evidence": ["ROE elevado", "Historico consistente de proventos"],
        "risks": ["Dependencia de juros e ciclo de credito"],
        "monitoring": ["Acompanhar sinistralidade, payout e regulacao"],
        "nextReviewDate": "2026-08-01",
    }


if __name__ == "__main__":
    unittest.main()
