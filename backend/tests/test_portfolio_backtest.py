from __future__ import annotations

from datetime import date
import unittest

from app.services.portfolio_backtest import build_current_portfolio_backtest_series


class PortfolioBacktestTests(unittest.TestCase):
    def test_builds_monthly_series_for_stocks_crypto_and_total(self) -> None:
        positions = [
            {"assetId": "stock-1", "class": "Acoes", "quantity": 10, "currentPrice": 15},
            {"assetId": "crypto-1", "class": "Cripto", "quantity": 2, "currentPrice": 30},
        ]
        histories = {
            "stock-1": [
                {"date": date(2025, 1, 1), "close": 10},
                {"date": date(2025, 1, 31), "close": 12},
                {"date": date(2025, 2, 28), "close": 15},
            ],
            "crypto-1": [
                {"date": date(2025, 1, 1), "close": 20},
                {"date": date(2025, 1, 31), "close": 10},
                {"date": date(2025, 2, 28), "close": 30},
            ],
        }

        rows = build_current_portfolio_backtest_series(positions, histories, date(2025, 1, 1), date(2025, 2, 28))

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["month"], "2025-01")
        self.assertEqual(rows[0]["stocksValue"], 100)
        self.assertEqual(rows[0]["cryptoValue"], 40)
        self.assertEqual(rows[0]["totalValue"], 140)
        self.assertEqual(rows[0]["monthlyReturnPct"], 0)
        self.assertEqual(rows[1]["totalValue"], 140)
        self.assertEqual(rows[1]["monthlyReturnPct"], 0)
        self.assertEqual(rows[2]["totalValue"], 210)
        self.assertEqual(rows[2]["monthlyReturnPct"], 50)
        self.assertEqual(rows[2]["cumulativeReturnPct"], 50)

    def test_normalizes_series_to_current_portfolio_value(self) -> None:
        positions = [
            {"assetId": "stock-1", "class": "Acoes", "quantity": 10, "currentPrice": 15},
        ]
        histories = {
            "stock-1": [
                {"date": date(2025, 1, 1), "close": 10},
                {"date": date(2025, 1, 31), "close": 10},
                {"date": date(2025, 2, 28), "close": 15},
            ],
        }

        rows = build_current_portfolio_backtest_series(
            positions,
            histories,
            date(2025, 1, 1),
            date(2025, 2, 28),
            baseline_value=1000,
        )

        self.assertEqual(rows[0]["totalValue"], 1000)
        self.assertEqual(rows[0]["baselineValue"], 1000)
        self.assertEqual(rows[2]["totalValue"], 1500)
        self.assertEqual(rows[2]["cumulativeReturnPct"], 50)

    def test_uses_current_value_by_asset_as_individual_baseline(self) -> None:
        positions = [
            {"assetId": "stock-1", "class": "Acoes", "quantity": 10, "currentPrice": 15},
            {"assetId": "crypto-1", "class": "Cripto", "quantity": 2, "currentPrice": 30},
        ]
        histories = {
            "stock-1": [
                {"date": date(2025, 1, 1), "close": 10},
                {"date": date(2025, 1, 31), "close": 10},
                {"date": date(2025, 2, 28), "close": 20},
            ],
            "crypto-1": [
                {"date": date(2025, 1, 1), "close": 20},
                {"date": date(2025, 1, 31), "close": 20},
                {"date": date(2025, 2, 28), "close": 10},
            ],
        }

        rows = build_current_portfolio_backtest_series(
            positions,
            histories,
            date(2025, 1, 1),
            date(2025, 2, 28),
            baseline_by_asset={"stock-1": 850, "crypto-1": 250},
        )

        self.assertEqual(rows[0]["stocksValue"], 850)
        self.assertEqual(rows[0]["cryptoValue"], 250)
        self.assertEqual(rows[0]["totalValue"], 1100)
        self.assertEqual(rows[2]["stocksValue"], 1700)
        self.assertEqual(rows[2]["cryptoValue"], 125)
        self.assertEqual(rows[2]["totalValue"], 1825)

    def test_applies_monthly_contributions_before_market_return(self) -> None:
        positions = [
            {"assetId": "stock-1", "class": "Acoes", "quantity": 10, "currentPrice": 15},
        ]
        histories = {
            "stock-1": [
                {"date": date(2025, 1, 1), "close": 10},
                {"date": date(2025, 1, 31), "close": 10},
                {"date": date(2025, 2, 28), "close": 20},
            ],
        }

        rows = build_current_portfolio_backtest_series(
            positions,
            histories,
            date(2025, 1, 1),
            date(2025, 2, 28),
            baseline_by_asset={"stock-1": 1000},
            monthly_contribution=200,
        )

        self.assertEqual(rows[0]["totalValue"], 1000)
        self.assertEqual(rows[1]["totalValue"], 1200)
        self.assertEqual(rows[1]["monthlyContribution"], 200)
        self.assertEqual(rows[1]["totalContributed"], 200)
        self.assertEqual(rows[1]["cumulativeReturnPct"], 0)
        self.assertEqual(rows[2]["totalValue"], 2800)
        self.assertEqual(rows[2]["totalContributed"], 400)
        self.assertEqual(rows[2]["capitalBaseValue"], 1400)
        self.assertEqual(rows[2]["performancePnl"], 1400)
        self.assertEqual(rows[2]["cumulativeReturnPct"], 100)

    def test_contributions_do_not_change_time_weighted_return(self) -> None:
        positions = [
            {"assetId": "stock-1", "class": "Acoes", "quantity": 10, "currentPrice": 15},
        ]
        histories = {
            "stock-1": [
                {"date": date(2025, 1, 1), "close": 10},
                {"date": date(2025, 1, 31), "close": 12},
                {"date": date(2025, 2, 28), "close": 15},
            ],
        }

        without_contribution = build_current_portfolio_backtest_series(
            positions,
            histories,
            date(2025, 1, 1),
            date(2025, 2, 28),
            baseline_by_asset={"stock-1": 1000},
            monthly_contribution=0,
        )
        with_contribution = build_current_portfolio_backtest_series(
            positions,
            histories,
            date(2025, 1, 1),
            date(2025, 2, 28),
            baseline_by_asset={"stock-1": 1000},
            monthly_contribution=200,
        )

        self.assertGreater(with_contribution[-1]["totalValue"], without_contribution[-1]["totalValue"])
        self.assertEqual(with_contribution[-1]["cumulativeReturnPct"], without_contribution[-1]["cumulativeReturnPct"])

    def test_separates_fixed_income_from_stocks(self) -> None:
        positions = [
            {"assetId": "stock-1", "class": "Acoes", "quantity": 10, "currentPrice": 15},
            {"assetId": "fixed-1", "class": "Renda fixa", "sector": "100% CDI", "quantity": 1, "currentPrice": 40000},
            {"assetId": "crypto-1", "class": "Cripto", "quantity": 2, "currentPrice": 30},
        ]
        histories = {
            "stock-1": [
                {"date": date(2025, 1, 1), "close": 10},
                {"date": date(2025, 1, 31), "close": 12},
            ],
            "crypto-1": [
                {"date": date(2025, 1, 1), "close": 20},
                {"date": date(2025, 1, 31), "close": 10},
            ],
        }

        rows = build_current_portfolio_backtest_series(positions, histories, date(2025, 1, 1), date(2025, 1, 31))

        self.assertEqual(rows[0]["stocksValue"], 100)
        self.assertEqual(rows[0]["cryptoValue"], 40)
        self.assertEqual(rows[0]["fixedIncomeValue"], 40000)
        self.assertEqual(rows[0]["totalValue"], 40140)


if __name__ == "__main__":
    unittest.main()
