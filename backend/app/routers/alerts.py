from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.alpha.alpha_score_engine import calculate_alpha_scores_v2
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Alert, User
from app.wealth_os.event_engine_v2 import build_event_payload_v2
from app.wealth_os.guardian_engine import ASSET_REVIEW_THRESHOLD


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = build_event_payload_v2(db, user.id)
    for alert in payload["alerts"]:
        alert["type"] = alert.get("eventType")
        alert["ticker"] = alert.get("asset")
        alert["isRead"] = alert.get("status") == "lido"
        if alert.get("source") == "guardian_v2":
            alert["source"] = "guardian"
    return payload


def _guardian_alerts(db: Session, user_id: str) -> list[dict]:
    """Compatibility adapter for legacy tests/extensions.

    The production route now uses Guardian 2.0 through Event Engine 2.0.
    This small adapter keeps the old private hook from behaving as a scary
    alert generator for neutral recommended assets.
    """
    alerts: list[dict] = []
    for row in calculate_alpha_scores_v2(db, user_id):
        if row.scoreFinal >= ASSET_REVIEW_THRESHOLD:
            continue
        alerts.append(
            {
                "id": f"guardian-asset-score-{row.assetId}",
                "type": "ativo_em_revisao",
                "category": "guardian",
                "severity": "warning",
                "title": f"{row.ticker} precisa de revisao de tese",
                "message": f"{row.ticker} marcou {row.scoreFinal:.0f}/100 no Alpha Score.",
                "impact": "Ativo abaixo do limite minimo de acompanhamento.",
                "recommendedAction": "Revisar tese, fundamentos e peso antes de aumentar exposicao.",
                "ticker": row.ticker,
                "isRead": False,
                "readOnly": True,
                "source": "guardian",
                "triggeredAt": "",
            }
        )
    return alerts


@router.post("/{alert_id}/read")
def mark_read(alert_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alert = db.get(Alert, alert_id)
    if alert and alert.user_id == user.id:
        alert.is_read = True
        db.commit()
    return {"ok": True}
