from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from math import isclose
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.engines.financial_projection_engine import FinancialProjectionEngine
from app.schemas import ProjectionRequest
from app.services.audit import write_audit_event
from app.services.data_lineage import record_data_evidence
from app.services.fixed_income import accrue_cdi_lots
from app.services.portfolio_backtest import build_current_portfolio_backtest_series


@dataclass(frozen=True)
class FormulaCase:
    id: str
    title: str
    formula: str
    runner: Callable[[], tuple[float, float, float, dict[str, Any]]]


def run_financial_formula_audit(db: Session | None = None) -> dict:
    """Run deterministic financial formula checks.

    This is not a unit-test replacement. It is an operational audit report that
    can be executed as a job in production and stored in the audit trail.
    """

    cases = _cases()
    rows = []
    for case in cases:
        try:
            actual, expected, tolerance, details = case.runner()
            passed = isclose(actual, expected, abs_tol=tolerance, rel_tol=0)
            rows.append(
                {
                    "id": case.id,
                    "title": case.title,
                    "formula": case.formula,
                    "status": "pass" if passed else "fail",
                    "actual": round(float(actual), 6),
                    "expected": round(float(expected), 6),
                    "tolerance": tolerance,
                    "details": details,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "id": case.id,
                    "title": case.title,
                    "formula": case.formula,
                    "status": "error",
                    "actual": None,
                    "expected": None,
                    "tolerance": None,
                    "details": {"error": str(exc)},
                }
            )

    passed_count = sum(1 for row in rows if row["status"] == "pass")
    failed = [row for row in rows if row["status"] != "pass"]
    score = round(passed_count / len(rows) * 100, 2) if rows else 0
    report = {
        "status": "pass" if not failed else "fail",
        "title": "Financial Formula Auditor",
        "generatedAt": datetime.now(UTC).isoformat(),
        "score": score,
        "passed": passed_count,
        "failed": len(failed),
        "cases": rows,
        "plainLanguage": [
            "Esta auditoria confere formulas financeiras com cenarios deterministicos e esperados conhecidos.",
            "Falha aqui deve bloquear deploy ou revisao institucional ate a formula ser corrigida.",
            "A auditoria nao valida preco de mercado; ela valida matematica, consistencia e separacao de conceitos.",
        ],
    }
    if db is not None:
        record_data_evidence(
            db,
            domain="financial_formula_audit",
            field_name="audit_score",
            value_numeric=score,
            unit="score_0_100",
            provider="financial_formula_auditor",
            source_type="formula",
            source_ref="financial_formula_auditor.run_financial_formula_audit",
            formula_name="financial_formula_audit_score",
            input_payload={"caseIds": [row["id"] for row in rows], "failed": len(failed)},
            confidence=100 if report["status"] == "pass" else 30,
            quality_score=100 if report["status"] == "pass" else 30,
            status=report["status"],
            metadata={"passed": passed_count, "failed": len(failed)},
        )
        for row in rows:
            record_data_evidence(
                db,
                domain="financial_formula_audit",
                field_name=row["id"],
                value_numeric=row["actual"],
                provider="financial_formula_auditor",
                source_type="formula",
                source_ref=row["formula"],
                formula_name=row["id"],
                input_payload=row.get("details") or {},
                confidence=100 if row["status"] == "pass" else 20,
                quality_score=100 if row["status"] == "pass" else 20,
                status=row["status"],
                metadata={"expected": row["expected"], "tolerance": row["tolerance"], "title": row["title"]},
            )
        write_audit_event(
            db,
            event_type="financial_formula_audit",
            category="financial_audit",
            action="run_formula_audit",
            actor_type="system",
            severity="info" if report["status"] == "pass" else "critical",
            message=f"Auditoria matematica finalizada com score {score:.0f}/100.",
            metadata=report,
        )
    return report


def _cases() -> list[FormulaCase]:
    return [
        FormulaCase(
            "required_wealth_for_income",
            "Patrimonio necessario para renda passiva",
            "meta_mensal * 12 / yield_anual",
            _case_required_wealth,
        ),
        FormulaCase(
            "contribution_only_projection",
            "Aporte sem retorno nao gera lucro",
            "patrimonio_final = patrimonio_inicial + soma_aportes",
            _case_contribution_only,
        ),
        FormulaCase(
            "passive_income_is_not_capital_gain",
            "Meta usa apenas renda passiva",
            "renda_passiva = patrimonio * yield_anual / 12",
            _case_passive_income_not_capital_gain,
        ),
        FormulaCase(
            "cdi_daily_compounding",
            "CDI diario composto",
            "valor_final = valor_inicial * produto(1 + taxa_diaria * percentual_cdi)",
            _case_cdi_daily_compounding,
        ),
        FormulaCase(
            "backtest_contribution_invariant",
            "Aporte nao altera rentabilidade time-weighted",
            "retorno_acumulado = produto(1 + retorno_mensal) - 1",
            _case_backtest_contribution_invariant,
        ),
        FormulaCase(
            "inflation_real_value",
            "Valor real desconta inflacao",
            "patrimonio_real = patrimonio_nominal / fator_inflacao",
            _case_real_value,
        ),
    ]


def _case_required_wealth() -> tuple[float, float, float, dict]:
    engine = FinancialProjectionEngine()
    actual = engine.required_wealth_for_income(15000, 7.5) or 0
    return actual, 2_400_000, 0.01, {"monthlyGoal": 15000, "annualYieldPct": 7.5}


def _case_contribution_only() -> tuple[float, float, float, dict]:
    engine = FinancialProjectionEngine()
    result = engine.simulate(
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
    return result["summary"]["finalValue"], 2200, 0.01, {"capitalGain": result["breakdown"]["capitalGain"]}


def _case_passive_income_not_capital_gain() -> tuple[float, float, float, dict]:
    engine = FinancialProjectionEngine()
    result = engine.simulate(
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
    return result["independence"]["monthlyPassiveIncome"], 0, 0.01, {"requiredWealth": result["independence"]["requiredWealth"]}


def _case_cdi_daily_compounding() -> tuple[float, float, float, dict]:
    result = accrue_cdi_lots(
        [{"date": date(2026, 1, 1), "amount": Decimal("1000")}],
        cdi_percent=Decimal("100"),
        end_date=date(2026, 1, 3),
        rates=[
            {"date": date(2026, 1, 2), "dailyPct": Decimal("0.10")},
            {"date": date(2026, 1, 3), "dailyPct": Decimal("0.10")},
        ],
    )
    return result["currentValue"], 1002.001, 0.02, {"appliedDays": result["appliedDays"], "source": result["source"]}


def _case_backtest_contribution_invariant() -> tuple[float, float, float, dict]:
    positions = [{"assetId": "stock-1", "class": "Acoes", "quantity": 10, "currentPrice": 15}]
    histories = {
        "stock-1": [
            {"date": date(2025, 1, 1), "close": 10},
            {"date": date(2025, 1, 31), "close": 12},
            {"date": date(2025, 2, 28), "close": 15},
        ]
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
    return (
        with_contribution[-1]["cumulativeReturnPct"],
        without_contribution[-1]["cumulativeReturnPct"],
        0.01,
        {"withContributionFinal": with_contribution[-1]["totalValue"], "withoutContributionFinal": without_contribution[-1]["totalValue"]},
    )


def _case_real_value() -> tuple[float, float, float, dict]:
    engine = FinancialProjectionEngine()
    return engine.real_value(1210, 1.21), 1000, 0.01, {"nominal": 1210, "inflationFactor": 1.21}
