from __future__ import annotations

import unittest
from datetime import date
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.routers import alerts as alerts_router
from app.database import Base
from app.models import Asset, MarketSnapshot, Transaction, User
from app.routers.alerts import list_alerts


class AlertsIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="michel@example.com", full_name="Michel", password_hash="hash")
        self.db.add(self.user)
        self.db.flush()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_alerts_include_alpha_events_when_manual_alerts_are_empty(self) -> None:
        asset = Asset(
            ticker="TEST3",
            name="Empresa Teste",
            asset_class="Acoes",
            sector="Energia",
            segment="Teste",
            currency="BRL",
            provider_symbol="TEST3",
            last_price=10,
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(
            MarketSnapshot(
                asset_id=asset.id,
                price=10,
                dividend_yield=0,
                payout=0,
                revenue_growth=-20,
                profit_growth=-25,
                net_margin=0,
                roe=0,
                roic=0,
                debt_to_ebitda=6,
                historical_appreciation=-20,
                dividend_consistency=0,
                payment_frequency=0,
                recurring_profit=0,
                sector_stability=30,
                pe_ratio=40,
                pvp=4,
            )
        )
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 7, 1),
                quantity=10,
                price=10,
                fees=0,
                broker="Alpha",
            )
        )
        self.db.commit()

        payload = list_alerts(self.db, self.user)

        self.assertGreater(payload["summary"]["alphaEvents"], 0)
        self.assertGreater(payload["summary"]["open"], 0)
        self.assertTrue(any(alert["source"] in {"alpha_engine", "guardian"} for alert in payload["alerts"]))
        self.assertTrue(any(alert["type"] == "concentracao_elevada" for alert in payload["alerts"]))

    def test_neutral_recommended_asset_does_not_become_scary_guardian_alert(self) -> None:
        original = alerts_router.calculate_alpha_scores_v2
        alerts_router.calculate_alpha_scores_v2 = lambda db, user_id: [
            SimpleNamespace(
                assetId="cpfe3-id",
                ticker="CPFE3",
                scoreFinal=54,
                classificacao="Neutro",
                justificativaFinal="Leitura neutra.",
                scores=[],
            )
        ]
        try:
            alerts = alerts_router._guardian_alerts(self.db, self.user.id)
        finally:
            alerts_router.calculate_alpha_scores_v2 = original

        self.assertFalse(any(alert.get("ticker") == "CPFE3" for alert in alerts))


if __name__ == "__main__":
    unittest.main()
