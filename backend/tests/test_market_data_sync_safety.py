from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, MarketSnapshot, Transaction, User
from app.services.market_data.sync import sync_asset_market_data, sync_user_assets
from app.services.market_data.v2.contracts import DATA_TYPE_FUNDAMENTALS, DATA_TYPE_PRICE_HISTORY, DATA_TYPE_QUOTE, NormalizedMarketData


class MarketDataSyncSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="sync@carteiraalpha.com", full_name="Sync User", password_hash="hash")
        self.db.add(self.user)
        self.db.flush()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_asset_sync_ignores_mock_records_even_if_provider_returns_them(self) -> None:
        asset = self._asset("BBDC4", "Acoes", Decimal("18.23"))
        mock_quote = NormalizedMarketData(
            data_type=DATA_TYPE_QUOTE,
            provider="mock",
            source_symbol="BBDC4",
            currency="BRL",
            payload={"price": 25.0},
        )

        with patch("app.services.market_data.sync.MarketDataEngine.collect", return_value=[mock_quote]):
            changed = sync_asset_market_data(self.db, asset)

        self.assertFalse(changed)
        self.assertEqual(float(asset.last_price), 18.23)
        self.assertEqual(float(asset.snapshot.price), 18.23)

    def test_portfolio_sync_replaces_previous_mock_price_with_history_fallback(self) -> None:
        asset = self._asset("BBDC4", "Acoes", Decimal("25.00"))
        self._transaction(asset, quantity=Decimal("7"), price=Decimal("12.56"))
        self.db.commit()
        history = NormalizedMarketData(
            data_type=DATA_TYPE_PRICE_HISTORY,
            provider="yahoo_finance",
            source_symbol="BBDC4",
            currency="BRL",
            payload={"prices": [{"date": "2026-07-18", "close": 18.86}]},
            quality_score=82,
        )

        def collect(data_type, request, include_mock=False):
            if data_type == DATA_TYPE_PRICE_HISTORY:
                return [history]
            if data_type in {DATA_TYPE_QUOTE, DATA_TYPE_FUNDAMENTALS}:
                return []
            return []

        with patch("app.services.market_data.sync.MarketDataEngine.collect", side_effect=collect), patch(
            "app.services.market_data.sync.MarketDataEngine.fetch",
            side_effect=AssertionError("sync must not use mock fallback fetch"),
        ):
            result = sync_user_assets(self.db, self.user.id)

        self.db.refresh(asset)
        self.assertEqual(result["updated"], ["BBDC4"])
        self.assertEqual(result["skipped"], [])
        self.assertEqual(result["repaired"], [])
        self.assertEqual(round(float(asset.last_price), 2), 18.86)
        self.assertEqual(round(float(asset.snapshot.price), 2), 18.86)

    def test_portfolio_sync_skips_fixed_income_in_market_quote_path(self) -> None:
        asset = self._asset("RDB RESGATE IMEDIATO", "Renda fixa", Decimal("40826.84"), sector="100% CDI")
        self._transaction(asset, quantity=Decimal("1"), price=Decimal("40826.84"))
        self.db.commit()

        with patch("app.services.portfolio.fetch_cdi_daily_rates", return_value=[]), patch(
            "app.services.market_data.sync.MarketDataEngine.collect",
            side_effect=AssertionError("fixed income must not be synced through quote providers"),
        ):
            result = sync_user_assets(self.db, self.user.id)

        self.db.refresh(asset)
        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"], ["RDB RESGATE IMEDIATO"])
        self.assertEqual(result["repaired"], [])
        self.assertEqual(round(float(asset.last_price), 2), 40826.84)

    def test_portfolio_sync_uses_crypto_repair_instead_of_generic_quote_path(self) -> None:
        asset = self._asset("SHIB", "Cripto", Decimal("25.00"), sector="Cripto", segment="meme coin")
        self._transaction(asset, quantity=Decimal("103.8533"), price=Decimal("0.000067"))
        self.db.commit()
        mock_quote = NormalizedMarketData(
            data_type=DATA_TYPE_QUOTE,
            provider="mock",
            source_symbol="SHIB",
            currency="BRL",
            payload={"price": 25.0},
        )

        with patch("app.services.crypto.MarketDataEngine.collect", return_value=[mock_quote]), patch(
            "app.services.crypto.CoinMarketCapProvider.get_quote",
            return_value=None,
        ):
            result = sync_user_assets(self.db, self.user.id)

        self.db.refresh(asset)
        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"], ["SHIB"])
        self.assertEqual(result["repaired"], ["SHIB"])
        self.assertAlmostEqual(float(asset.last_price), 0.000067, places=8)
        self.assertAlmostEqual(float(asset.snapshot.price), 0.000067, places=8)

    def _asset(
        self,
        ticker: str,
        asset_class: str,
        price: Decimal,
        *,
        sector: str = "Bancos",
        segment: str = "Cadastro manual",
    ) -> Asset:
        asset = Asset(
            ticker=ticker,
            name=ticker,
            asset_class=asset_class,
            sector=sector,
            segment=segment,
            currency="BRL",
            provider_symbol=ticker,
            last_price=price,
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(MarketSnapshot(asset_id=asset.id, price=price, dividend_yield=0, payout=0))
        self.db.flush()
        return asset

    def _transaction(self, asset: Asset, *, quantity: Decimal, price: Decimal) -> None:
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 7, 1),
                quantity=quantity,
                price=price,
                fees=Decimal("0"),
                broker="Alpha",
            )
        )


if __name__ == "__main__":
    unittest.main()
