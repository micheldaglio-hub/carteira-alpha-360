from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.engines.asset_engine import ensure_asset_engine_metadata
from app.models import Asset, AssetIdentifier, MarketSnapshot, Transaction, User
from app.services.portfolio import get_positions


class AssetEngineCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_brazilian_equity_keeps_legacy_fields_and_gets_universal_identity(self) -> None:
        asset = Asset(
            ticker="WEGE3",
            name="WEG ON",
            asset_class="Acoes",
            sector="Bens industriais",
            segment="Motores e equipamentos",
            currency="BRL",
            provider_symbol="WEGE3",
            last_price=Decimal("41.90"),
        )

        ensure_asset_engine_metadata(self.db, asset, force=True)
        self.db.commit()

        self.assertEqual(asset.ticker, "WEGE3")
        self.assertEqual(asset.asset_class, "Acoes")
        self.assertEqual(asset.currency, "BRL")
        self.assertEqual(asset.universal_symbol, "BR:B3:WEGE3")
        self.assertEqual(asset.asset_subclass, "Brazilian Equity")
        self.assertEqual(asset.country_code, "BR")
        self.assertEqual(asset.market, "B3")

        identifiers = self.db.execute(select(AssetIdentifier).where(AssetIdentifier.asset_id == asset.id)).scalars().all()
        self.assertTrue(any(item.identifier_type == "universal_symbol" for item in identifiers))
        self.assertTrue(any(item.identifier_type == "ticker" for item in identifiers))

    def test_crypto_asset_gets_crypto_market_identity_without_changing_legacy_class(self) -> None:
        asset = Asset(
            ticker="BTC",
            name="Bitcoin",
            asset_class="Cripto",
            sector="Cripto",
            segment="reserva de valor",
            currency="BRL",
            provider_symbol="BTC",
            last_price=Decimal("350000"),
        )

        ensure_asset_engine_metadata(self.db, asset, force=True)
        self.db.commit()

        self.assertEqual(asset.asset_class, "Cripto")
        self.assertEqual(asset.universal_symbol, "CRYPTO:BTC")
        self.assertEqual(asset.market, "Crypto")
        self.assertEqual(asset.base_currency, "BTC")
        self.assertEqual(asset.trading_currency, "BRL")

    def test_portfolio_position_payload_remains_backward_compatible(self) -> None:
        user = User(
            email="compat@carteiraalpha.com",
            full_name="Compat User",
            password_hash="hash",
        )
        self.db.add(user)
        self.db.flush()

        asset = Asset(
            ticker="ITSA4",
            name="Itausa PN",
            asset_class="Acoes",
            sector="Holding financeira",
            segment="Financeiro",
            currency="BRL",
            provider_symbol="ITSA4",
            last_price=Decimal("10.72"),
        )
        ensure_asset_engine_metadata(self.db, asset, force=True)
        self.db.add(MarketSnapshot(asset_id=asset.id, price=Decimal("10.72"), dividend_yield=0, payout=0))
        self.db.add(
            Transaction(
                user_id=user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 1, 10),
                quantity=Decimal("10"),
                price=Decimal("9.50"),
                fees=Decimal("1.00"),
                broker="Compat Broker",
                notes="",
            )
        )
        self.db.commit()

        positions = get_positions(self.db, user.id)

        self.assertEqual(len(positions), 1)
        self.assertEqual(
            set(positions[0].keys()),
            {
                "assetId",
                "ticker",
                "name",
                "class",
                "sector",
                "segment",
                "quantity",
                "averagePrice",
                "currentPrice",
                "investedValue",
                "currentValue",
                "pnl",
                "returnPct",
                "dividendYieldOnAvg",
                "dividendsReceived",
                "transactions",
                "fees",
                "weight",
            },
        )
        self.assertNotIn("universalSymbol", positions[0])
        self.assertNotIn("countryCode", positions[0])


if __name__ == "__main__":
    unittest.main()
