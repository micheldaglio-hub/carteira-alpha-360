from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import ProjectionRequest
from app.services.data_lineage_integrations import record_projection_evidence
from app.services.portfolio import get_dashboard
from app.services.projection_premises import delete_projection_premises, get_projection_premises, save_projection_premises
from app.services.projections import simulate_projection


router = APIRouter(prefix="/projections", tags=["projections"])


@router.post("/simulate")
def simulate(payload: ProjectionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dashboard = get_dashboard(db, current_user.id)
    current_wealth = float(dashboard.get("metrics", {}).get("totalEquity") or payload.initial_wealth)
    result = simulate_projection(payload, current_wealth_for_goal=current_wealth)
    result["dataLineage"] = record_projection_evidence(db, current_user.id, payload, result, current_wealth)
    return result


@router.get("/premises")
def saved_premises(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"premises": get_projection_premises(db, current_user.id)}


@router.put("/premises")
def save_premises(payload: ProjectionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"saved": True, "premises": save_projection_premises(db, current_user.id, payload)}


@router.delete("/premises")
def reset_premises(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_projection_premises(db, current_user.id)
    return {"deleted": True}
