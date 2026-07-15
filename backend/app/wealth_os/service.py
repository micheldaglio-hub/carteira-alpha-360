from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.portfolio import get_dashboard
from app.wealth_os.contracts import WealthCommandCenter, to_dict
from app.wealth_os.copilot_service import build_copilot_questions
from app.wealth_os.data_confidence_engine import build_data_confidence
from app.wealth_os.economic_engine import build_economic_readings
from app.wealth_os.event_engine_v2 import build_event_stream_v2
from app.wealth_os.goal_engine import build_goals
from app.wealth_os.guardian_engine import build_guardian_report
from app.wealth_os.opportunity_engine import build_opportunities
from app.wealth_os.research_news_engine import build_research_center
from app.wealth_os.scenario_engine import build_scenarios, build_stress_test_report
from app.wealth_os.strategy_engine import build_strategy_report
from app.wealth_os.tax_engine import build_tax_report
from app.wealth_os.utils import greeting
from app.wealth_os.wealth_progress_engine import build_wealth_progress_score


def build_command_center(db: Session, user_id: str) -> WealthCommandCenter:
    dashboard = get_dashboard(db, user_id)
    metrics = dashboard["metrics"]
    events = build_event_stream_v2(db, user_id)
    score = build_wealth_progress_score(db, user_id)
    goals = build_goals(db, user_id)
    opportunities = build_opportunities(db, user_id)
    scenarios = build_scenarios(db, user_id)
    confidence = build_data_confidence(db, user_id)
    questions = build_copilot_questions(db, user_id)
    top_goal = next((goal for goal in goals if goal.id == "passive_income"), goals[0] if goals else None)

    if top_goal and top_goal.remainingValue > 0:
        mission = f"Missao atual: reduzir a distancia para {top_goal.title}."
    else:
        mission = "Missao atual: manter consistencia, dados completos e risco controlado."

    return WealthCommandCenter(
        greeting=greeting(),
        headline="O Alpha Wealth OS consolidou patrimonio, metas, risco, oportunidades e confiabilidade dos dados.",
        mission=mission,
        totalWealth=metrics["totalEquity"],
        investedValue=metrics["investedValue"],
        pnlPct=metrics["pnlPct"],
        passiveIncome=metrics["projectedPassiveIncome"],
        eventsCount=len(events),
        wealthProgressScore=score,
        topGoals=goals[:4],
        opportunities=opportunities[:3],
        scenarios=scenarios[:3],
        dataConfidence=confidence,
        copilotQuestions=questions[:6],
    )


def build_wealth_os_payload(db: Session, user_id: str) -> dict:
    return {
        "commandCenter": to_dict(build_command_center(db, user_id)),
        "goals": to_dict(build_goals(db, user_id)),
        "wealthProgressScore": to_dict(build_wealth_progress_score(db, user_id)),
        "scenarios": to_dict(build_scenarios(db, user_id)),
        "stressTestReport": to_dict(build_stress_test_report(db, user_id)),
        "opportunities": to_dict(build_opportunities(db, user_id)),
        "economicReadings": to_dict(build_economic_readings(db, user_id)),
        "dataConfidence": to_dict(build_data_confidence(db, user_id)),
        "copilotQuestions": to_dict(build_copilot_questions(db, user_id)),
        "eventStream": to_dict(build_event_stream_v2(db, user_id)),
        "guardian": to_dict(build_guardian_report(db, user_id)),
        "researchCenter": to_dict(build_research_center(db, user_id, limit=6)),
        "taxReport": to_dict(build_tax_report(db, user_id)),
        "strategyReport": to_dict(build_strategy_report(db, user_id)),
    }
