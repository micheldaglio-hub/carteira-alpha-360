from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi import Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import CopilotChatRequest
from app.services.data_lineage_integrations import (
    record_copilot_evidence,
    record_macro_fx_evidence,
    record_stress_evidence,
    record_strategy_evidence,
    record_tax_evidence,
)
from app.wealth_os.contracts import to_dict
from app.wealth_os.copilot_service import answer_question, ask_copilot, build_copilot_questions, copilot_status
from app.wealth_os.data_confidence_engine import build_data_confidence
from app.wealth_os.economic_engine import build_economic_readings
from app.wealth_os.event_engine_v2 import build_event_payload_v2
from app.wealth_os.goal_engine import build_goals
from app.wealth_os.guardian_engine import build_guardian_report
from app.wealth_os.macro_fx_engine import build_macro_fx_snapshot
from app.wealth_os.opportunity_engine import build_opportunities
from app.wealth_os.research_news_engine import build_asset_research_report, build_research_center
from app.wealth_os.scenario_engine import build_scenarios, build_stress_test_report
from app.wealth_os.service import build_command_center, build_wealth_os_payload
from app.wealth_os.strategy_engine import build_strategy_report
from app.wealth_os.tax_engine import build_tax_report
from app.wealth_os.wealth_progress_engine import build_wealth_progress_score


router = APIRouter(prefix="/wealth-os", tags=["wealth-os"])


@router.get("")
def wealth_os(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return build_wealth_os_payload(db, user.id)


@router.get("/command-center")
def command_center(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return to_dict(build_command_center(db, user.id))


@router.get("/goals")
def goals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"goals": to_dict(build_goals(db, user.id))}


@router.get("/score")
def score(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"wealthProgressScore": to_dict(build_wealth_progress_score(db, user.id))}


@router.get("/scenarios")
def scenarios(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"scenarios": to_dict(build_scenarios(db, user.id))}


@router.get("/stress-test")
def stress_test(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = to_dict(build_stress_test_report(db, user.id))
    payload["dataLineage"] = record_stress_evidence(db, user.id, payload)
    return payload


@router.get("/opportunities")
def opportunities(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"opportunities": to_dict(build_opportunities(db, user.id))}


@router.get("/economic")
def economic(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"economicReadings": to_dict(build_economic_readings(db, user.id))}


@router.get("/macro-fx")
def macro_fx(
    refresh: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = to_dict(build_macro_fx_snapshot(db, user.id, refresh=refresh))
    payload["dataLineage"] = record_macro_fx_evidence(db, user.id, payload)
    return payload


@router.get("/fx")
def fx(
    refresh: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    snapshot = build_macro_fx_snapshot(db, user.id, refresh=refresh)
    payload = {
        "status": snapshot.status,
        "updatedAt": snapshot.updatedAt,
        "fxRates": to_dict(snapshot.fxRates),
        "sourceHealth": to_dict(snapshot.sourceHealth),
        "warnings": snapshot.warnings,
    }
    payload["dataLineage"] = record_macro_fx_evidence(db, user.id, {"fxRates": payload["fxRates"]})
    return payload


@router.get("/tax")
def tax_report(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = to_dict(build_tax_report(db, user.id, year=year, month=month))
    payload["dataLineage"] = record_tax_evidence(db, user.id, payload)
    return payload


@router.get("/strategies")
def strategies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = to_dict(build_strategy_report(db, user.id))
    payload["dataLineage"] = record_strategy_evidence(db, user.id, payload)
    return payload


@router.get("/events")
def events(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return build_event_payload_v2(db, user.id)


@router.get("/guardian")
def guardian(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"guardian": to_dict(build_guardian_report(db, user.id))}


@router.get("/research")
def research_center(
    limit: int = Query(default=12, ge=1, le=30),
    refresh_news: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return to_dict(build_research_center(db, user.id, limit=limit, refresh_news=refresh_news))


@router.get("/research/{ticker}")
def asset_research(
    ticker: str,
    refresh_news: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return to_dict(build_asset_research_report(db, user.id, ticker, refresh_news=refresh_news))


@router.get("/data-confidence")
def data_confidence(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"dataConfidence": to_dict(build_data_confidence(db, user.id))}


@router.get("/copilot/questions")
def copilot_questions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"questions": to_dict(build_copilot_questions(db, user.id))}


@router.get("/copilot/answer/{question_id}")
def copilot_answer(question_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = answer_question(db, user.id, question_id)
    payload["dataLineage"] = record_copilot_evidence(db, user.id, payload)
    return payload


@router.get("/copilot/status")
def copilot_runtime_status(user: User = Depends(get_current_user)):
    return copilot_status()


@router.post("/copilot/chat")
def copilot_chat(payload: CopilotChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    response = ask_copilot(db, user.id, payload.message, payload.conversation_id)
    response["dataLineage"] = record_copilot_evidence(db, user.id, response)
    return response
