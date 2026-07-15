from __future__ import annotations

import unittest

from app.services.asset_taxonomy import CLASS_RENDA_FIXA_BRASIL, classify_position
from app.services.portfolio_aggregation import build_portfolio_snapshot
from app.wealth_os.scenario_engine import _build_exposures
from app.wealth_os.strategy_engine import _bucket_for


class FinancialReliabilityInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.positions = [
            {
                "assetId": "rdb",
                "ticker": "RDB RESGATE IMEDIATO",
                "name": "RDB Resgate Imediato",
                "class": "Renda fixa",
                "sector": "100% CDI",
                "segment": "Pos-Fixado",
                "quantity": 1,
                "investedValue": 40826.64,
                "currentValue": 40826.64,
                "pnl": 0,
                "dividendYieldOnAvg": 0,
                "fixedIncome": {"cdiPercent": 100, "dailyRatePct": 0.047},
            },
            {
                "assetId": "bbdc4",
                "ticker": "BBDC4",
                "name": "Bradesco",
                "class": "Acoes",
                "sector": "Bancos",
                "segment": "Banco",
                "quantity": 7,
                "investedValue": 123.90,
                "currentValue": 132.02,
                "pnl": 8.12,
                "dividendYieldOnAvg": 6.0,
            },
            {
                "assetId": "xrp",
                "ticker": "XRP",
                "name": "XRP",
                "class": "Cripto",
                "sector": "Cripto",
                "segment": "Cryptoasset",
                "quantity": 30.208,
                "investedValue": 171.27,
                "currentValue": 166.40,
                "pnl": -4.87,
                "dividendYieldOnAvg": 0,
            },
        ]
        self.external_accounts = [
            {
                "ticker": "Trading Desk EV+",
                "name": "Trading Desk EV+",
                "class": "Trading",
                "sector": "Estrategias",
                "currentValue": 87.59,
                "investedValue": 100.0,
                "pnl": -12.41,
                "currency": "BRL",
                "country": "BR",
            }
        ]

    def test_snapshot_allocations_sum_to_equity_and_weights_sum_to_100(self) -> None:
        snapshot = build_portfolio_snapshot(self.positions, external_accounts=self.external_accounts)
        class_rows = snapshot["allocations"]["byClass"]

        self.assertAlmostEqual(sum(row["value"] for row in class_rows), snapshot["totals"]["currentValue"], places=2)
        self.assertAlmostEqual(sum(row["weight"] for row in class_rows), 100.0, places=1)
        self.assertTrue(snapshot["consistency"]["isBalanced"])

    def test_fixed_income_is_not_equity_global_or_dividend_income(self) -> None:
        taxonomy = classify_position(self.positions[0])

        self.assertEqual(taxonomy.asset_class, CLASS_RENDA_FIXA_BRASIL)
        self.assertEqual(taxonomy.strategy_bucket, "Caixa/Renda Fixa")
        self.assertFalse(taxonomy.is_global_exposure)
        self.assertFalse(taxonomy.is_traditional_passive_income)
        self.assertTrue(taxonomy.is_fixed_income)
        self.assertEqual(_bucket_for(self.positions[0], None), "Caixa/Renda Fixa")

    def test_crypto_is_not_traditional_passive_income(self) -> None:
        taxonomy = classify_position(self.positions[2])

        self.assertTrue(taxonomy.is_crypto)
        self.assertFalse(taxonomy.is_traditional_passive_income)

    def test_pnl_respects_current_minus_invested_without_double_counting(self) -> None:
        snapshot = build_portfolio_snapshot(self.positions, external_accounts=self.external_accounts)
        expected_current = 40826.64 + 132.02 + 166.40 + 87.59
        expected_invested = 40826.64 + 123.90 + 171.27 + 100.0

        self.assertAlmostEqual(snapshot["totals"]["currentValue"], expected_current, places=2)
        self.assertAlmostEqual(snapshot["totals"]["investedValue"], expected_invested, places=2)
        self.assertAlmostEqual(snapshot["totals"]["pnl"], expected_current - expected_invested, places=2)

    def test_stress_engine_keeps_fixed_income_in_own_bucket(self) -> None:
        dashboard = {
            "metrics": {"externalEquity": 0},
            "portfolioSnapshot": build_portfolio_snapshot(self.positions, external_accounts=[]),
        }
        exposures = _build_exposures(self.positions, {}, dashboard)

        self.assertAlmostEqual(exposures["Renda Fixa Brasil"], 40826.64, places=2)
        self.assertAlmostEqual(exposures["Acoes Brasil"], 132.02, places=2)
        self.assertAlmostEqual(exposures["Cripto"], 166.40, places=2)
        self.assertNotIn("Global", exposures)


if __name__ == "__main__":
    unittest.main()
