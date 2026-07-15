from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.portfolio import get_dashboard, get_positions
from app.services.projection_premises import get_dashboard_projection_premises, get_projection_premises
from app.wealth_os.contracts import WealthGoal, clamp
from app.wealth_os.utils import as_float, estimate_months_to_target, required_monthly_contribution


def _premises(db: Session, user_id: str) -> dict:
    projection = get_projection_premises(db, user_id) or {}
    dashboard = get_dashboard_projection_premises(db, user_id) or {}
    return {
        "monthly_contribution": as_float(
            projection.get("monthly_contribution", dashboard.get("monthly_contribution", 0))
        ),
        "monthly_return": as_float(
            projection.get("expected_monthly_return", dashboard.get("monthly_return", 0))
        ),
        "passive_income_goal": as_float(projection.get("passive_income_goal", 5000)),
        "annual_yield": as_float(projection.get("expected_annual_dividend_yield", 7.5)),
    }


def _goal(
    *,
    goal_id: str,
    title: str,
    description: str,
    current: float,
    target: float,
    monthly_contribution: float,
    monthly_return: float,
    months: int = 120,
    confidence: str = "media",
    assumptions: list[str] | None = None,
) -> WealthGoal:
    progress = clamp((current / target * 100) if target > 0 else 0)
    estimated = estimate_months_to_target(current, target, monthly_contribution, monthly_return)
    required = required_monthly_contribution(current, target, months, monthly_return)
    remaining = max(0, target - current)
    status = "atingida" if remaining <= 0 else "em_andamento" if progress >= 20 else "inicio"
    return WealthGoal(
        id=goal_id,
        title=title,
        description=description,
        currentValue=round(current, 2),
        targetValue=round(target, 2),
        progressPct=round(progress, 2),
        remainingValue=round(remaining, 2),
        estimatedMonths=estimated,
        requiredMonthlyContribution=required,
        status=status,
        confidence=confidence,
        assumptions=assumptions or [],
    )


def build_goals(db: Session, user_id: str) -> list[WealthGoal]:
    dashboard = get_dashboard(db, user_id)
    positions = get_positions(db, user_id)
    metrics = dashboard["metrics"]
    premises = _premises(db, user_id)
    total_wealth = as_float(metrics.get("totalEquity"))
    passive_income = as_float(metrics.get("projectedPassiveIncome"))
    monthly_contribution = premises["monthly_contribution"]
    monthly_return = premises["monthly_return"]
    annual_yield = premises["annual_yield"]
    passive_goal = premises["passive_income_goal"]
    required_wealth_for_income = passive_goal * 12 / (annual_yield / 100) if annual_yield > 0 else 0

    international_value = 0.0
    crypto_value = 0.0
    for item in positions:
        class_name = str(item.get("class") or "").lower()
        sector = str(item.get("sector") or "").lower()
        ticker = str(item.get("ticker") or "").upper()
        if class_name in {"cripto", "crypto"}:
            crypto_value += as_float(item.get("currentValue"))
        if "exterior" in sector or ticker in {"AAPL", "MSFT", "GOOGL", "AMZN", "IVVB11", "VOO", "VT", "VTI", "QQQ"}:
            international_value += as_float(item.get("currentValue"))

    international_target = total_wealth * 0.2
    crypto_cap_target = total_wealth * 0.1

    return [
        _goal(
            goal_id="first_100k",
            title="Primeiros R$ 100 mil",
            description="Marco inicial de acumulacao patrimonial com disciplina de aportes.",
            current=total_wealth,
            target=100000,
            monthly_contribution=monthly_contribution,
            monthly_return=monthly_return,
            months=120,
            confidence="media",
            assumptions=["Usa patrimonio total atual e premissas salvas pelo usuario."],
        ),
        _goal(
            goal_id="first_1m",
            title="Primeiro R$ 1 milhao",
            description="Meta de patrimonio para acelerar renda passiva e opcionalidade financeira.",
            current=total_wealth,
            target=1000000,
            monthly_contribution=monthly_contribution,
            monthly_return=monthly_return,
            months=240,
            confidence="media",
            assumptions=["Nao e promessa de retorno; e uma simulacao com aporte e retorno informados."],
        ),
        _goal(
            goal_id="passive_income",
            title="Renda passiva mensal",
            description="Meta calculada apenas com renda distribuida, sem misturar valorizacao de patrimonio.",
            current=passive_income,
            target=passive_goal,
            monthly_contribution=monthly_contribution,
            monthly_return=monthly_return,
            months=240,
            confidence="media",
            assumptions=[f"Yield anual usado: {annual_yield:.2f}% a.a.", f"Patrimonio necessario estimado: R$ {required_wealth_for_income:,.2f}."],
        ),
        _goal(
            goal_id="global_exposure",
            title="Diversificacao global",
            description="Base para reduzir dependencia exclusiva de Brasil, real e risco local.",
            current=international_value,
            target=international_target,
            monthly_contribution=monthly_contribution,
            monthly_return=monthly_return,
            months=60,
            confidence="baixa" if international_target == 0 else "media",
            assumptions=["Meta inicial tecnica: 20% do patrimonio com exposicao internacional."],
        ),
        _goal(
            goal_id="crypto_control",
            title="Cripto sob controle",
            description="Cripto pode acelerar a carteira, mas precisa ficar dentro de um limite de risco definido.",
            current=min(crypto_value, crypto_cap_target),
            target=crypto_cap_target,
            monthly_contribution=0,
            monthly_return=0,
            months=1,
            confidence="media",
            assumptions=["Limite tecnico inicial: cripto ate 10% do patrimonio total."],
        ),
    ]

