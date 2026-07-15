from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import DashboardProjectionPremises
from app.services.data_lineage_integrations import record_dashboard_evidence
from app.services.projection_premises import (
    delete_dashboard_projection_premises,
    get_dashboard_projection_premises,
    save_dashboard_projection_premises,
)
from app.services.portfolio import get_dashboard


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = get_dashboard(db, user.id)
    payload["dataLineage"] = record_dashboard_evidence(db, user.id, payload)
    return payload


@router.get("/projection-premises")
def projection_premises(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"premises": get_dashboard_projection_premises(db, user.id)}


@router.put("/projection-premises")
def save_projection_premises(
    payload: DashboardProjectionPremises,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return {"saved": True, "premises": save_dashboard_projection_premises(db, user.id, payload)}


@router.delete("/projection-premises")
def reset_projection_premises(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_dashboard_projection_premises(db, user.id)
    return {"deleted": True}
