from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, MarketDataCacheEntry, MarketDataProviderEvent, Transaction, User
from app.wealth_os.macro_fx_engine import EconomicMacroFxEngine


class MacroFxEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="macro@carteiraalpha.com", full_name="Macro User", password_hash="hash")
        self.db.add(self.user)
        self.db.flush()
        asset = Asset(
            ticker="BBSE3",
            name="BB Seguridade",
            asset_class="Acoes",
            sector="Seguros",
            segment="Seguridade",
            last_price=Decimal("35"),
            provider_symbol="BBSE3",
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 7, 1),
                quantity=Decimal("10"),
                price=Decimal("33"),
                fees=Decimal("0"),
                broker="Alpha",
            )
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_macro_fx_snapshot_uses_bcb_sgs_and_writes_cache(self) -> None:
        engine = EconomicMacroFxEngine(client_factory=lambda: httpx.Client(transport=httpx.MockTransport(_bcb_handler)))

        snapshot = engine.build_snapshot(self.db, self.user.id)

        self.assertEqual(snapshot.status, "real_time")
        self.assertEqual(len(snapshot.indicators), 3)
        self.assertEqual(len(snapshot.fxRates), 2)
        self.assertEqual(next(item.value for item in snapshot.indicators if item.id == "selic_meta"), 10.5)
        self.assertGreater(next(item.value for item in snapshot.indicators if item.id == "ipca_12m"), 0)
        self.assertEqual(next(item.rate for item in snapshot.fxRates if item.pair == "USD/BRL"), 5.4321)
        self.assertTrue(snapshot.portfolioReadings)

        rows = self.db.execute(select(MarketDataCacheEntry)).scalars().all()
        self.assertGreaterEqual(len(rows), 5)
        self.assertTrue(all(row.provider == "bcb_sgs" for row in rows))

    def test_macro_fx_snapshot_falls_back_to_stale_cache_when_provider_fails(self) -> None:
        success = EconomicMacroFxEngine(client_factory=lambda: httpx.Client(transport=httpx.MockTransport(_bcb_handler)))
        success.build_snapshot(self.db, self.user.id)

        failing = EconomicMacroFxEngine(
            client_factory=lambda: httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503, json={"erro": "offline"})))
        )
        snapshot = failing.build_snapshot(self.db, self.user.id, refresh=True)

        self.assertIn("provider_unavailable", snapshot.warnings)
        self.assertIn("stale_cache", snapshot.warnings)
        self.assertGreater(next(item.rate for item in snapshot.fxRates if item.pair == "USD/BRL"), 0)

        events = self.db.execute(select(MarketDataProviderEvent)).scalars().all()
        self.assertGreaterEqual(len(events), 1)


def _bcb_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "bcdata.sgs.432" in url:
        return httpx.Response(
            200,
            json=[
                {"data": "01/02/2026", "valor": "10.50"},
                {"data": "01/03/2026", "valor": "10.50"},
                {"data": "01/04/2026", "valor": "10.50"},
            ],
        )
    if "bcdata.sgs.433" in url:
        return httpx.Response(
            200,
            json=[
                {"data": "01/08/2025", "valor": "0.32"},
                {"data": "01/09/2025", "valor": "0.28"},
                {"data": "01/10/2025", "valor": "0.45"},
                {"data": "01/11/2025", "valor": "0.38"},
                {"data": "01/12/2025", "valor": "0.41"},
                {"data": "01/01/2026", "valor": "0.30"},
                {"data": "01/02/2026", "valor": "0.26"},
                {"data": "01/03/2026", "valor": "0.36"},
                {"data": "01/04/2026", "valor": "0.42"},
                {"data": "01/05/2026", "valor": "0.33"},
                {"data": "01/06/2026", "valor": "0.25"},
                {"data": "01/07/2026", "valor": "0.29"},
            ],
        )
    if "bcdata.sgs.10813" in url:
        return httpx.Response(200, json=[{"data": "10/07/2026", "valor": "5.4321"}])
    if "bcdata.sgs.21619" in url:
        return httpx.Response(200, json=[{"data": "10/07/2026", "valor": "6.2222"}])
    return httpx.Response(404, json={"erro": "serie desconhecida"})


if __name__ == "__main__":
    unittest.main()
