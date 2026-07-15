from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.alpha.alpha_score_engine import calculate_alpha_scores_v2
from app.alpha.contracts import to_dict
from app.alpha.copilot import build_copilot_interface
from app.alpha.event_engine import build_portfolio_events
from app.alpha.health_engine import calculate_health
from app.alpha.insight_engine import build_insights
from app.alpha.timeline_engine import build_timeline
from app.alpha.utils import money, percent
from app.services.portfolio import get_dashboard, get_positions


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia."
    if hour < 18:
        return "Boa tarde."
    return "Boa noite."


def get_summary(db: Session, user_id: str) -> dict:
    dashboard = get_dashboard(db, user_id)
    positions = get_positions(db, user_id)
    events = build_timeline(build_portfolio_events(db, user_id))
    health = calculate_health(db, user_id)
    insights = build_insights(db, user_id, events)
    metrics = dashboard["metrics"]
    important_events = [event for event in events if event.gravidade in {"warning", "critical", "success"}]
    attention = next((event for event in events if event.gravidade in {"warning", "critical"}), None)
    top_position = max(positions, key=lambda item: item["weight"], default=None)

    bullets = [
        f"Hoje existem {len(important_events)} eventos importantes para acompanhamento.",
        f"Sua carteira registra retorno acumulado de {percent(metrics['pnlPct'])}.",
        f"Voce recebeu {money(metrics['dividendsMonth'])} em proventos no mes.",
        f"Seu Score Alpha esta em {health.notaGeral:.0f}/100.",
    ]
    if top_position and top_position["weight"] >= 20:
        bullets.append(f"{top_position['ticker']} merece atencao por concentracao de {percent(top_position['weight'])}.")
    elif insights:
        bullets.append(insights[0].titulo)

    return {
        "greeting": _greeting(),
        "headline": "O Alpha Intelligence Engine consolidou eventos, saude e pontos de atencao da carteira.",
        "eventsCount": len(events),
        "importantEventsCount": len(important_events),
        "portfolioChangePct": metrics["pnlPct"],
        "dividendsMonth": metrics["dividendsMonth"],
        "scoreAlpha": health.notaGeral,
        "goalDeltaMonths": None,
        "attention": attention.titulo if attention else None,
        "bullets": bullets,
        "health": to_dict(health),
        "topInsights": to_dict(insights[:3]),
    }


def get_timeline(db: Session, user_id: str) -> dict:
    return {"events": to_dict(build_timeline(build_portfolio_events(db, user_id)))}


def get_health(db: Session, user_id: str) -> dict:
    return to_dict(calculate_health(db, user_id))


def get_insights(db: Session, user_id: str) -> dict:
    events = build_timeline(build_portfolio_events(db, user_id))
    return {"insights": to_dict(build_insights(db, user_id, events))}


def get_alpha_scores(db: Session, user_id: str) -> dict:
    return {"scores": to_dict(calculate_alpha_scores_v2(db, user_id))}


def get_copilot(db: Session, user_id: str) -> dict:
    return build_copilot_interface(db, user_id)
