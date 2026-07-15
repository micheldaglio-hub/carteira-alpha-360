from __future__ import annotations

from sqlalchemy.orm import Session

from app.alpha.health_engine import calculate_health
from app.services.portfolio import get_allocations, get_dashboard, get_positions
from app.wealth_os.contracts import WealthProgressFactor, WealthProgressScore, clamp
from app.wealth_os.goal_engine import build_goals
from app.wealth_os.utils import as_float, status_from_score


def _factor(name: str, score: float, reading: str, impact: str) -> WealthProgressFactor:
    normalized = round(clamp(score), 2)
    return WealthProgressFactor(
        name=name,
        score=normalized,
        status=status_from_score(normalized),
        reading=reading,
        impact=impact,
    )


def build_wealth_progress_score(db: Session, user_id: str) -> WealthProgressScore:
    dashboard = get_dashboard(db, user_id)
    positions = get_positions(db, user_id)
    allocations = get_allocations(positions)
    health = calculate_health(db, user_id)
    goals = build_goals(db, user_id)
    metrics = dashboard["metrics"]
    total_equity = as_float(metrics.get("totalEquity"))
    pnl_pct = as_float(metrics.get("pnlPct"))
    largest_asset = max((as_float(item.get("weight")) for item in positions), default=0)
    largest_sector = max((as_float(item.get("weight")) for item in allocations.get("bySector", [])), default=0)
    asset_count = len(positions)
    class_count = len({item.get("class") for item in positions})
    goal_progress = sum(goal.progressPct for goal in goals[:3]) / 3 if goals else 0
    passive_income = as_float(metrics.get("projectedPassiveIncome"))

    concentration_score = 100 - max(0, largest_asset - 12) * 2.5 - max(0, largest_sector - 35) * 1.4
    diversification_score = min(100, asset_count * 5 + class_count * 12)
    momentum_score = 55 + pnl_pct * 3
    income_score = min(100, passive_income * 8)

    factors = [
        _factor(
            "Meta patrimonial",
            goal_progress,
            "Mede o avanco nas metas de R$ 100 mil, R$ 1 milhao e renda passiva.",
            "Mostra se a carteira esta virando patrimonio real no longo prazo.",
        ),
        _factor(
            "Diversificacao",
            diversification_score,
            f"A carteira tem {asset_count} ativos distribuidos em {class_count} classes.",
            "Mais classes e setores reduzem dependencia de um unico evento.",
        ),
        _factor(
            "Concentracao",
            concentration_score,
            f"Maior ativo esta em {largest_asset:.2f}% e maior setor em {largest_sector:.2f}%.",
            "Concentracao alta aumenta o impacto de erro em uma tese especifica.",
        ),
        _factor(
            "Renda passiva",
            income_score,
            f"Renda mensal projetada atual: R$ {passive_income:,.2f}.",
            "Indica quanto a carteira ja ajuda na independencia financeira.",
        ),
        _factor(
            "Saude Alpha",
            as_float(health.notaGeral),
            f"Score Alpha atual: {health.notaGeral:.0f}/100.",
            "Resume qualidade, risco, valuation e estabilidade da carteira.",
        ),
        _factor(
            "Momento da carteira",
            momentum_score,
            f"Retorno acumulado atual: {pnl_pct:.2f}%.",
            "Nao e previsao; e leitura do resultado registrado ate agora.",
        ),
    ]
    weights = {
        "Meta patrimonial": 0.22,
        "Diversificacao": 0.16,
        "Concentracao": 0.18,
        "Renda passiva": 0.14,
        "Saude Alpha": 0.2,
        "Momento da carteira": 0.1,
    }
    score = sum(item.score * weights[item.name] for item in factors)
    normalized_score = round(clamp(score), 2)

    strengths = [item.reading for item in factors if item.score >= 70][:3]
    attention = [item.reading for item in factors if item.score < 60][:3]
    next_actions = []
    if total_equity <= 0:
        next_actions.append("Registrar os primeiros ativos para o Alpha montar a leitura patrimonial.")
    if largest_asset >= 20:
        next_actions.append("Avaliar concentracao do maior ativo antes de aumentar exposicao nele.")
    if passive_income <= 0:
        next_actions.append("Registrar proventos e JCP para o motor acompanhar renda passiva real.")
    if not next_actions:
        next_actions.append("Manter aportes planejados e revisar a carteira no proximo ciclo do Guardian.")

    return WealthProgressScore(
        score=normalized_score,
        status=status_from_score(normalized_score),
        headline=f"Seu Wealth Progress Score esta em {normalized_score:.0f}/100.",
        factors=factors,
        strengths=strengths,
        attentionPoints=attention,
        nextActions=next_actions,
    )

