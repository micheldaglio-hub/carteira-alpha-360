from __future__ import annotations

from datetime import date
import unittest

from app.services.portfolio import _month_performance_start, _month_start_price, _price_at_or_before, get_portfolio_summary


class PortfolioSummaryTests(unittest.TestCase):
    def test_summary_separates_stocks_crypto_and_total(self) -> None:
        positions = [
            {
                "class": "Acoes",
                "quantity": 2,
                "investedValue": 100.0,
                "currentValue": 110.0,
                "pnl": 10.0,
            },
            {
                "class": "Acoes",
                "quantity": 3,
                "investedValue": 90.0,
                "currentValue": 81.0,
                "pnl": -9.0,
            },
            {
                "class": "Cripto",
                "quantity": 1.5,
                "investedValue": 50.0,
                "currentValue": 75.0,
                "pnl": 25.0,
            },
        ]

        summary = get_portfolio_summary(positions)

        self.assertEqual(summary["stocks"]["assetCount"], 2)
        self.assertEqual(summary["stocks"]["quantity"], 5)
        self.assertEqual(summary["stocks"]["pnl"], 1)
        self.assertEqual(summary["crypto"]["assetCount"], 1)
        self.assertEqual(summary["crypto"]["returnPct"], 50)
        self.assertEqual(summary["total"]["assetCount"], 3)
        self.assertEqual(summary["total"]["pnl"], 26)

    def test_month_performance_uses_previous_month_base_like_backtest(self) -> None:
        self.assertEqual(_month_performance_start(date(2026, 7, 15)), date(2026, 6, 30))

    def test_month_start_price_uses_first_price_at_or_after_base(self) -> None:
        prices = [
            {"date": date(2026, 6, 28), "close": 10.0},
            {"date": date(2026, 7, 1), "close": 11.0},
        ]

        self.assertEqual(_month_start_price(prices, date(2026, 6, 30), 99.0), 11.0)

    def test_rolling_30_price_uses_price_at_or_before_target(self) -> None:
        prices = [
            {"date": date(2026, 6, 17), "close": 10.0},
            {"date": date(2026, 6, 18), "close": 11.0},
            {"date": date(2026, 6, 19), "close": 12.0},
        ]

        self.assertEqual(_price_at_or_before(prices, date(2026, 6, 18), 99.0), 11.0)
        self.assertEqual(_price_at_or_before(prices, date(2026, 6, 16), 99.0), 10.0)


if __name__ == "__main__":
    unittest.main()
