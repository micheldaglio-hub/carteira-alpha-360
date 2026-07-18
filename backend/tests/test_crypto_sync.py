from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, MarketSnapshot, Transaction, User
from app.services.crypto import sync_crypto_asset, sync_user_crypto
from app.services.market_data.v2.contracts import DATA_TYPE_PRICE_HISTORY, DATA_TYPE_QUOTE, MarketDataRequest, NormalizedMarketData
from app.services.market_data.v2.providers.coingecko import CoinGeckoProviderV2
from app.services.portfolio import get_positions, get_positions_with_month_performance


class CryptoSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="crypto@carteiraalpha.com", full_name="Crypto User", password_hash="hash")
        self.db.add(self.user)
        self.db.flush()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_sync_does_not_persist_generic_mock_crypto_price(self) -> None:
        asset = Asset(
            ticker="VET",
            name="VeChain",
            asset_class="Cripto",
            sector="Cripto",
            segment="reserva de valor",
            currency="BRL",
            provider_symbol="VET",
            last_price=Decimal("25.00"),
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(MarketSnapshot(asset_id=asset.id, price=Decimal("25.00"), dividend_yield=0, payout=0))
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 7, 1),
                quantity=Decimal("646.2531"),
                price=Decimal("0.02"),
                fees=Decimal("0"),
                broker="Binance",
            )
        )
        self.db.commit()
        mock_quote = NormalizedMarketData(
            data_type=DATA_TYPE_QUOTE,
            provider="mock",
            source_symbol="VET",
            currency="BRL",
            payload={"price": 25.0},
        )

        with patch("app.services.crypto.MarketDataEngine.collect", return_value=[mock_quote]), patch(
            "app.services.crypto.CoinMarketCapProvider.get_quote",
            return_value=None,
        ):
            result = sync_user_crypto(self.db, self.user.id)

        self.db.refresh(asset)
        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"], ["VET"])
        self.assertEqual(result["repaired"], ["VET"])
        self.assertEqual(round(float(asset.last_price), 2), 0.02)
        self.assertEqual(round(float(asset.snapshot.price), 2), 0.02)

    def test_sync_repairs_generic_mock_price_for_tiny_crypto_from_ledger(self) -> None:
        asset = Asset(
            ticker="SHIB",
            name="Shiba Inu",
            asset_class="Cripto",
            sector="Cripto",
            segment="meme coin",
            currency="BRL",
            provider_symbol="SHIB",
            last_price=Decimal("25.00"),
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(MarketSnapshot(asset_id=asset.id, price=Decimal("25.00"), dividend_yield=0, payout=0))
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 7, 1),
                quantity=Decimal("103.8533"),
                price=Decimal("0.000067"),
                fees=Decimal("0"),
                broker="Binance",
            )
        )
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
            result = sync_user_crypto(self.db, self.user.id)

        self.db.refresh(asset)
        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"], ["SHIB"])
        self.assertEqual(result["repaired"], ["SHIB"])
        self.assertAlmostEqual(float(asset.last_price), 0.000067, places=8)
        self.assertAlmostEqual(float(asset.snapshot.price), 0.000067, places=8)

    def test_sync_crypto_ignores_twelvedata_bogus_price_and_uses_coingecko(self) -> None:
        asset = Asset(
            ticker="FLR",
            name="Flare",
            asset_class="Cripto",
            sector="Cripto",
            segment="infraestrutura",
            currency="BRL",
            provider_symbol="FLR",
            last_price=Decimal("25.00"),
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(MarketSnapshot(asset_id=asset.id, price=Decimal("25.00"), dividend_yield=0, payout=0))
        self.db.commit()
        twelvedata_quote = NormalizedMarketData(
            data_type=DATA_TYPE_QUOTE,
            provider="twelvedata",
            source_symbol="FLR",
            currency="USD",
            payload={"price": 49.08},
            quality_score=70,
        )
        coingecko_quote = NormalizedMarketData(
            data_type=DATA_TYPE_QUOTE,
            provider="coingecko",
            source_symbol="FLR",
            currency="BRL",
            payload={"price": 0.03334873},
            quality_score=84,
        )

        with patch("app.services.crypto.MarketDataEngine.collect", return_value=[twelvedata_quote, coingecko_quote]):
            changed = sync_crypto_asset(self.db, asset)

        self.assertTrue(changed)
        self.assertAlmostEqual(float(asset.last_price), 0.03334873, places=8)
        self.assertAlmostEqual(float(asset.snapshot.price), 0.03334873, places=8)

    def test_sync_repairs_generic_mock_price_for_btc_from_ledger_when_providers_fail(self) -> None:
        asset = Asset(
            ticker="BTC",
            name="Bitcoin",
            asset_class="Cripto",
            sector="Cripto",
            segment="reserva de valor",
            currency="BRL",
            provider_symbol="BTC",
            last_price=Decimal("25.00"),
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(MarketSnapshot(asset_id=asset.id, price=Decimal("25.00"), dividend_yield=0, payout=0))
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 7, 1),
                quantity=Decimal("0.001"),
                price=Decimal("320476.36"),
                fees=Decimal("0"),
                broker="Binance",
            )
        )
        self.db.commit()
        mock_quote = NormalizedMarketData(
            data_type=DATA_TYPE_QUOTE,
            provider="mock",
            source_symbol="BTC",
            currency="BRL",
            payload={"price": 25.0},
        )

        with patch("app.services.crypto.MarketDataEngine.collect", return_value=[mock_quote]), patch(
            "app.services.crypto.CoinMarketCapProvider.get_quote",
            return_value=None,
        ):
            result = sync_user_crypto(self.db, self.user.id)

        self.db.refresh(asset)
        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"], ["BTC"])
        self.assertEqual(result["repaired"], ["BTC"])
        self.assertEqual(round(float(asset.last_price), 2), 320476.36)

    def test_coingecko_quote_uses_coin_id_for_low_price_tokens(self) -> None:
        provider = CoinGeckoProviderV2()
        request = MarketDataRequest(symbol="SHIB", market="Crypto", asset_class="Cripto", currency="BRL")

        with patch.object(
            provider,
            "_get",
            return_value={"shiba-inu": {"brl": 0.000067, "brl_market_cap": 1000, "brl_24h_change": 1.2}},
        ) as mocked_get:
            quote = provider.fetch(DATA_TYPE_QUOTE, request)

        mocked_get.assert_called_once()
        self.assertEqual(mocked_get.call_args.args[0], "simple/price")
        self.assertIn("shiba-inu", mocked_get.call_args.args[1]["ids"])
        self.assertEqual(quote.provider, "coingecko")
        self.assertAlmostEqual(quote.payload["price"], 0.000067, places=8)
        self.assertEqual(quote.payload["raw"]["provider_id"], "shiba-inu")

    def test_crypto_position_payload_keeps_tiny_price_precision(self) -> None:
        asset = Asset(
            ticker="SHIB",
            name="Shiba Inu",
            asset_class="Cripto",
            sector="Cripto",
            segment="meme coin",
            currency="BRL",
            provider_symbol="SHIB",
            last_price=Decimal("0.00002127"),
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(MarketSnapshot(asset_id=asset.id, price=Decimal("0.00002127"), dividend_yield=0, payout=0))
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 7, 1),
                quantity=Decimal("103.8533"),
                price=Decimal("0.000067"),
                fees=Decimal("0"),
                broker="Binance",
            )
        )
        self.db.commit()

        [position] = get_positions(self.db, self.user.id)

        self.assertGreater(position["currentPrice"], 0)
        self.assertLess(position["currentPrice"], 0.0001)
        self.assertEqual(position["averagePrice"], 0.000067)

    def test_tiny_crypto_month_performance_uses_precise_current_value(self) -> None:
        asset = Asset(
            ticker="SHIB",
            name="Shiba Inu",
            asset_class="Cripto",
            sector="Cripto",
            segment="meme coin",
            currency="BRL",
            provider_symbol="SHIB",
            last_price=Decimal("0.00002127"),
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(MarketSnapshot(asset_id=asset.id, price=Decimal("0.00002127"), dividend_yield=0, payout=0))
        self.db.add(
            Transaction(
                user_id=self.user.id,
                asset_id=asset.id,
                type="buy",
                date=date(2026, 7, 1),
                quantity=Decimal("103.8533"),
                price=Decimal("0.000067"),
                fees=Decimal("0"),
                broker="Binance",
            )
        )
        self.db.commit()
        today = date.today()
        month_start_anchor = date(today.year, today.month, 1) - timedelta(days=1)
        history = NormalizedMarketData(
            data_type=DATA_TYPE_PRICE_HISTORY,
            provider="coingecko",
            source_symbol="SHIB",
            currency="BRL",
            payload={
                "prices": [
                    {"date": month_start_anchor.isoformat(), "close": 0.00002},
                    {"date": today.isoformat(), "close": 0.00002127},
                ]
            },
            quality_score=84,
        )

        with patch("app.services.portfolio.MarketDataEngine.collect", return_value=[history]):
            [position] = get_positions_with_month_performance(self.db, self.user.id)

        self.assertGreater(position["monthReturnPct"], -99)
        self.assertGreater(position["monthReturnPct"], 0)


if __name__ == "__main__":
    unittest.main()
