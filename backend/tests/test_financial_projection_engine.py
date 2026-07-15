from __future__ import annotations

import unittest

from app.engines.financial_projection_engine import FinancialProjectionEngine
from app.schemas import ProjectionRequest


class FinancialProjectionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = FinancialProjectionEngine()

    def test_zero_wealth_zero_contribution_returns_zero(self) -> None:
        result = self.engine.simulate(
            ProjectionRequest(
                initial_wealth=0,
                monthly_contribution=0,
                expected_monthly_return=0,
                expected_annual_dividend_yield=0,
                reinvest_dividends=False,
                annual_inflation=0,
                years=1,
                passive_income_goal=0,
            )
        )

        self.assertEqual(result["summary"]["finalValue"], 0)
        self.assertEqual(result["breakdown"]["capitalGain"], 0)
        self.assertEqual(result["independence"]["monthlyPassiveIncome"], 0)

    def test_contribution_only_has_no_capital_gain_or_dividends(self) -> None:
        result = self.engine.simulate(
            ProjectionRequest(
                initial_wealth=1000,
                monthly_contribution=100,
                expected_monthly_return=0,
                expected_annual_dividend_yield=0,
                reinvest_dividends=False,
                annual_inflation=0,
                years=1,
                passive_income_goal=0,
            )
        )

        self.assertEqual(result["summary"]["finalValue"], 2200)
        self.assertEqual(result["summary"]["totalContributed"], 2200)
        self.assertEqual(result["breakdown"]["capitalGain"], 0)
        self.assertEqual(result["breakdown"]["passiveIncomeTotal"], 0)

    def test_goal_uses_only_passive_income_not_capital_gain(self) -> None:
        result = self.engine.simulate(
            ProjectionRequest(
                initial_wealth=100000,
                monthly_contribution=5000,
                expected_monthly_return=2,
                expected_annual_dividend_yield=0,
                reinvest_dividends=False,
                annual_inflation=0,
                years=10,
                passive_income_goal=100,
            )
        )

        self.assertEqual(result["independence"]["monthlyPassiveIncome"], 0)
        self.assertIsNone(result["independence"]["requiredWealth"])
        self.assertIsNone(result["summary"]["estimatedMonthsToGoal"])

    def test_independence_remaining_wealth_uses_current_wealth_not_final_projection(self) -> None:
        result = self.engine.simulate(
            ProjectionRequest(
                initial_wealth=1000,
                monthly_contribution=250,
                expected_monthly_return=1.65,
                expected_annual_dividend_yield=7.5,
                reinvest_dividends=True,
                annual_inflation=4,
                years=20,
                passive_income_goal=15000,
            ),
            current_wealth_for_goal=1191.32,
        )

        self.assertEqual(result["independence"]["requiredWealth"], 2400000)
        self.assertEqual(result["independence"]["currentWealthForGoal"], 1191.32)
        self.assertEqual(result["independence"]["remainingWealthToGoal"], 2398808.68)
        self.assertLess(result["independence"]["currentGoalProgressPct"], 1)
        self.assertGreater(result["independence"]["projectedGoalProgressPct"], 100)

    def test_partial_reinvestment_separates_reinvested_and_withdrawn_income(self) -> None:
        result = self.engine.simulate(
            ProjectionRequest(
                initial_wealth=10000,
                monthly_contribution=0,
                expected_monthly_return=0,
                expected_annual_dividend_yield=12,
                reinvest_dividends=True,
                dividend_reinvestment_rate=50,
                annual_inflation=0,
                years=1,
                passive_income_goal=0,
            )
        )

        self.assertGreater(result["breakdown"]["reinvestedDividends"], 0)
        self.assertGreater(result["breakdown"]["withdrawnDividends"], 0)
        self.assertAlmostEqual(
            result["breakdown"]["reinvestedDividends"],
            result["breakdown"]["withdrawnDividends"],
            delta=0.05,
        )

    def test_projection_exposes_proceeds_semantics_without_breaking_legacy_keys(self) -> None:
        result = self.engine.simulate(
            ProjectionRequest(
                initial_wealth=10000,
                monthly_contribution=0,
                expected_monthly_return=0,
                expected_annual_dividend_yield=12,
                reinvest_dividends=True,
                dividend_reinvestment_rate=100,
                annual_inflation=0,
                years=1,
                passive_income_goal=0,
            )
        )

        self.assertEqual(result["summary"]["totalProceeds"], result["summary"]["totalDividends"])
        self.assertEqual(result["breakdown"]["proceedsTotal"], result["breakdown"]["passiveIncomeTotal"])
        self.assertEqual(result["breakdown"]["reinvestedProceeds"], result["breakdown"]["reinvestedDividends"])
        self.assertIn("proventos", result["assumptions"]["passiveIncomeInterpretation"])

    def test_high_inflation_reduces_real_wealth(self) -> None:
        result = self.engine.simulate(
            ProjectionRequest(
                initial_wealth=10000,
                monthly_contribution=0,
                expected_monthly_return=0,
                expected_annual_dividend_yield=0,
                reinvest_dividends=False,
                annual_inflation=20,
                years=5,
                passive_income_goal=0,
            )
        )

        self.assertLess(result["breakdown"]["finalReal"], result["breakdown"]["finalNominal"])

    def test_negative_return_is_supported(self) -> None:
        result = self.engine.simulate(
            ProjectionRequest(
                initial_wealth=10000,
                monthly_contribution=0,
                expected_monthly_return=-1,
                expected_annual_dividend_yield=0,
                reinvest_dividends=False,
                annual_inflation=0,
                years=1,
                passive_income_goal=0,
            )
        )

        self.assertLess(result["summary"]["finalValue"], 10000)
        self.assertLess(result["breakdown"]["capitalGain"], 0)

    def test_fifty_year_horizon_returns_annual_series(self) -> None:
        result = self.engine.simulate(
            ProjectionRequest(
                initial_wealth=1000,
                monthly_contribution=100,
                expected_monthly_return=0.5,
                expected_annual_dividend_yield=5,
                reinvest_dividends=True,
                annual_inflation=3,
                years=50,
                passive_income_goal=5000,
            )
        )

        self.assertEqual(result["series"][-1]["month"], 600)
        self.assertGreater(result["summary"]["finalValue"], result["summary"]["totalContributed"])


if __name__ == "__main__":
    unittest.main()
