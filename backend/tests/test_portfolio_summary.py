from __future__ import annotations

import unittest

from app.services.portfolio import get_portfolio_summary


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


if __name__ == "__main__":
    unittest.main()
