from __future__ import annotations

from dataclasses import dataclass

from app.schemas import ProjectionRequest


@dataclass(frozen=True)
class ProjectionYearAssumptions:
    monthly_capital_gain_rate: float
    monthly_passive_yield_rate: float
    monthly_inflation_rate: float
    monthly_contribution: float


class FinancialProjectionEngine:
    """Single source of truth for financial projections.

    Concepts:
    - Capital gain is asset appreciation only.
    - Passive income is distributed cash flow only: dividends, JCP, FII income, REITs, coupons and interest.
    - Reinvested passive income returns to wealth; withdrawn income does not.
    - Financial independence is measured only by passive income.
    """

    def simulate(self, payload: ProjectionRequest, *, current_wealth_for_goal: float | None = None) -> dict:
        months = payload.years * 12
        wealth = float(payload.initial_wealth)
        initial_wealth = float(payload.initial_wealth)
        current_wealth = float(initial_wealth if current_wealth_for_goal is None else max(current_wealth_for_goal, 0))
        contributed_after_initial = 0.0
        total_contributed = initial_wealth
        total_capital_gain = 0.0
        total_passive_income = 0.0
        reinvested_income = 0.0
        withdrawn_income = 0.0
        cumulative_inflation_factor = 1.0
        target_month = None
        rows: list[dict] = []

        reinvestment_rate = self._reinvestment_rate(payload)
        required_wealth = self.required_wealth_for_income(
            payload.passive_income_goal,
            payload.expected_annual_dividend_yield,
        )

        for month in range(1, months + 1):
            year_index = (month - 1) // 12
            assumptions = self._assumptions_for_month(payload, year_index)

            contribution = assumptions.monthly_contribution
            wealth += contribution
            contributed_after_initial += contribution
            total_contributed += contribution

            capital_gain = wealth * assumptions.monthly_capital_gain_rate
            wealth += capital_gain
            total_capital_gain += capital_gain

            passive_income = wealth * assumptions.monthly_passive_yield_rate
            total_passive_income += passive_income

            reinvested = passive_income * reinvestment_rate
            withdrawn = passive_income - reinvested
            reinvested_income += reinvested
            withdrawn_income += withdrawn
            wealth += reinvested

            cumulative_inflation_factor *= 1 + assumptions.monthly_inflation_rate
            real_wealth = self.real_value(wealth, cumulative_inflation_factor)
            passive_income_monthly = wealth * assumptions.monthly_passive_yield_rate

            if target_month is None and payload.passive_income_goal > 0 and passive_income_monthly >= payload.passive_income_goal:
                target_month = month

            if month == 1 or month % 12 == 0:
                rows.append(
                    {
                        "month": month,
                        "year": round(month / 12, 1),
                        "equity": round(wealth, 2),
                        "realEquity": round(real_wealth, 2),
                        "contributed": round(total_contributed, 2),
                        "dividends": round(total_passive_income, 2),
                        "passiveIncome": round(passive_income_monthly, 2),
                        "capitalGain": round(total_capital_gain, 2),
                        "reinvestedDividends": round(reinvested_income, 2),
                        "withdrawnDividends": round(withdrawn_income, 2),
                        "inflationFactor": round(cumulative_inflation_factor, 6),
                    }
                )

        final_real = self.real_value(wealth, cumulative_inflation_factor)
        passive_income_final = wealth * self._annual_yield_for_year(payload, payload.years - 1) / 100 / 12
        current_passive_income = current_wealth * payload.expected_annual_dividend_yield / 100 / 12
        total_return = total_capital_gain + total_passive_income
        real_gain = final_real - total_contributed
        inflation_accumulated_pct = (cumulative_inflation_factor - 1) * 100
        current_goal_progress_pct = (
            current_passive_income / payload.passive_income_goal * 100 if payload.passive_income_goal else 0
        )
        projected_goal_progress_pct = (
            passive_income_final / payload.passive_income_goal * 100 if payload.passive_income_goal else 0
        )
        remaining_wealth_to_goal = (
            max(required_wealth - current_wealth, 0) if required_wealth is not None else None
        )

        breakdown = {
            "initialWealth": round(initial_wealth, 2),
            "finalNominal": round(wealth, 2),
            "finalReal": round(final_real, 2),
            "capitalContributed": round(total_contributed, 2),
            "monthlyContributionsTotal": round(contributed_after_initial, 2),
            "capitalGain": round(total_capital_gain, 2),
            "passiveIncomeTotal": round(total_passive_income, 2),
            "proceedsTotal": round(total_passive_income, 2),
            "reinvestedDividends": round(reinvested_income, 2),
            "withdrawnDividends": round(withdrawn_income, 2),
            "reinvestedProceeds": round(reinvested_income, 2),
            "withdrawnProceeds": round(withdrawn_income, 2),
            "inflationAccumulatedPct": round(inflation_accumulated_pct, 2),
            "realGain": round(real_gain, 2),
            "totalReturn": round(total_return, 2),
        }

        independence = {
            "monthlyPassiveIncome": round(passive_income_final, 2),
            "currentPassiveIncome": round(current_passive_income, 2),
            "monthlyGoal": round(payload.passive_income_goal, 2),
            "goalProgressPct": round(current_goal_progress_pct, 2),
            "currentGoalProgressPct": round(current_goal_progress_pct, 2),
            "projectedGoalProgressPct": round(projected_goal_progress_pct, 2),
            "remainingMonthlyIncome": round(max(payload.passive_income_goal - current_passive_income, 0), 2),
            "remainingMonthlyIncomeAtEnd": round(max(payload.passive_income_goal - passive_income_final, 0), 2),
            "remainingWealthToGoal": round(remaining_wealth_to_goal, 2) if remaining_wealth_to_goal is not None else None,
            "requiredWealth": round(required_wealth, 2) if required_wealth is not None else None,
            "currentWealthForGoal": round(current_wealth, 2),
            "estimatedMonthsToGoal": target_month,
            "estimatedYearsToGoal": round(target_month / 12, 1) if target_month else None,
            "yieldUsedAnnualPct": payload.expected_annual_dividend_yield,
            "premises": {
                "goalUsesOnlyPassiveIncome": True,
                "formula": "patrimonio * yield_anual / 12",
                "remainingWealthFormula": "patrimonio_necessario - patrimonio_atual",
            },
        }

        growth_sources = [
            {"name": "Capital aportado", "value": round(total_contributed, 2)},
            {"name": "Valorizacao", "value": round(total_capital_gain, 2)},
            {"name": "Proventos reinvestidos", "value": round(reinvested_income, 2)},
            {"name": "Proventos sacados", "value": round(withdrawn_income, 2)},
            {"name": "Inflacao acumulada", "value": round(max(wealth - final_real, 0), 2)},
            {"name": "Ganho real", "value": round(real_gain, 2)},
        ]

        summary = {
            "finalValue": round(wealth, 2),
            "totalContributed": round(total_contributed, 2),
            "totalDividends": round(total_passive_income, 2),
            "totalProceeds": round(total_passive_income, 2),
            "totalInterest": round(total_capital_gain, 2),
            "estimatedMonthsToGoal": target_month,
            "estimatedYearsToGoal": round(target_month / 12, 1) if target_month else None,
        }

        assumptions = {
            "monthlyReturnPct": payload.expected_monthly_return,
            "monthlyDividendYieldPct": round(payload.expected_annual_dividend_yield / 12, 4),
            "effectiveMonthlyReturnPct": round(
                (
                    (1 + payload.expected_monthly_return / 100)
                    * (1 + (payload.expected_annual_dividend_yield / 100 / 12 * reinvestment_rate))
                    - 1
                )
                * 100,
                4,
            ),
            "dividendsReinvested": reinvestment_rate > 0,
            "dividendReinvestmentRatePct": round(reinvestment_rate * 100, 2),
            "annualContributionGrowthPct": payload.annual_contribution_growth,
            "returnInterpretation": "Rentabilidade mensal informada e tratada como ganho de preco, separada dos proventos.",
            "passiveIncomeInterpretation": "Yield anual representa proventos totais: dividendos, JCP, rendimentos de FIIs, REITs, juros, cupons e outras distribuicoes.",
        }

        return {
            "summary": summary,
            "assumptions": assumptions,
            "series": rows,
            "breakdown": breakdown,
            "independence": independence,
            "growthSources": growth_sources,
            "intelligentReading": self._reading(breakdown, independence),
            "formulas": self.formulas(),
            "disclaimer": "Simulacao baseada em premissas informadas. Capital gain, proventos, renda passiva e inflacao sao tratados separadamente. Nao promete rentabilidade futura.",
        }

    def dashboard_projection(self, *, initial_wealth: float, monthly_contribution: float, monthly_return_pct: float, years: int) -> float:
        payload = ProjectionRequest(
            initial_wealth=initial_wealth,
            monthly_contribution=monthly_contribution,
            expected_monthly_return=monthly_return_pct,
            expected_annual_dividend_yield=0,
            reinvest_dividends=False,
            annual_inflation=0,
            years=years,
            passive_income_goal=0,
        )
        return self.simulate(payload)["summary"]["finalValue"]

    def required_wealth_for_income(self, monthly_goal: float, annual_yield_pct: float) -> float | None:
        if monthly_goal <= 0 or annual_yield_pct <= 0:
            return None
        return monthly_goal * 12 / (annual_yield_pct / 100)

    def real_value(self, nominal_value: float, cumulative_inflation_factor: float) -> float:
        if cumulative_inflation_factor <= 0:
            return nominal_value
        return nominal_value / cumulative_inflation_factor

    def formulas(self) -> dict[str, str]:
        return {
            "capitalGain": "patrimonio_apos_aporte * rentabilidade_mensal",
            "passiveIncome": "patrimonio_apos_valorizacao * yield_anual_de_proventos / 12",
            "reinvestedIncome": "renda_passiva * percentual_reinvestimento",
            "withdrawnIncome": "renda_passiva - proventos_reinvestidos",
            "finalWealth": "patrimonio + aportes + valorizacao + proventos_reinvestidos",
            "realWealth": "patrimonio_nominal / fator_inflacao_acumulado",
            "requiredWealthForGoal": "meta_mensal * 12 / yield_anual",
            "goalProgress": "renda_passiva_mensal / meta_mensal",
            "remainingWealthToGoal": "max(patrimonio_necessario - patrimonio_atual, 0)",
        }

    def _reading(self, breakdown: dict, independence: dict) -> dict:
        return {
            "title": "Como seu patrimonio cresceu",
            "description": (
                f"Seu patrimonio final foi de R$ {breakdown['finalNominal']:,.2f}. "
                f"Desse valor, R$ {breakdown['capitalContributed']:,.2f} vieram dos aportes, "
                f"R$ {breakdown['capitalGain']:,.2f} vieram da valorizacao dos ativos e "
                f"R$ {breakdown['reinvestedProceeds']:,.2f} vieram do reinvestimento de proventos. "
                f"O patrimonio real descontando inflacao corresponde a R$ {breakdown['finalReal']:,.2f}."
            ),
            "bullets": [
                f"R$ {breakdown['capitalContributed']:,.2f} vieram dos aportes.",
                f"R$ {breakdown['capitalGain']:,.2f} vieram da valorizacao dos ativos.",
                f"R$ {breakdown['reinvestedProceeds']:,.2f} vieram de proventos reinvestidos.",
                f"Renda passiva mensal estimada: R$ {independence['monthlyPassiveIncome']:,.2f}.",
            ],
        }

    def _assumptions_for_month(self, payload: ProjectionRequest, year_index: int) -> ProjectionYearAssumptions:
        annual_inflation = self._value_for_year(payload.variable_annual_inflation, year_index, payload.annual_inflation)
        monthly_contribution = payload.monthly_contribution * (
            (1 + payload.annual_contribution_growth / 100) ** year_index
        )
        return ProjectionYearAssumptions(
            monthly_capital_gain_rate=self._monthly_return_for_year(payload, year_index) / 100,
            monthly_passive_yield_rate=self._annual_yield_for_year(payload, year_index) / 100 / 12,
            monthly_inflation_rate=(1 + annual_inflation / 100) ** (1 / 12) - 1,
            monthly_contribution=monthly_contribution,
        )

    def _monthly_return_for_year(self, payload: ProjectionRequest, year_index: int) -> float:
        return self._value_for_year(payload.variable_monthly_returns, year_index, payload.expected_monthly_return)

    def _annual_yield_for_year(self, payload: ProjectionRequest, year_index: int) -> float:
        return self._value_for_year(
            payload.variable_annual_dividend_yields,
            year_index,
            payload.expected_annual_dividend_yield,
        )

    def _value_for_year(self, values: list[float], year_index: int, default: float) -> float:
        if values and year_index < len(values):
            return float(values[year_index])
        return float(default)

    def _reinvestment_rate(self, payload: ProjectionRequest) -> float:
        if payload.dividend_reinvestment_rate is not None:
            return max(0.0, min(1.0, payload.dividend_reinvestment_rate / 100))
        return 1.0 if payload.reinvest_dividends else 0.0
