from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.portfolio import get_positions
from app.services.scoring import list_scores


router = APIRouter(prefix="/radar", tags=["radar"])


def _is_scoreable_asset(position: dict) -> bool:
    asset_class = str(position.get("class") or "").lower()
    return asset_class not in {"cripto", "crypto", "renda fixa", "fixed income"}


@router.get("/assets")
def assets_radar(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    positions = get_positions(db, user.id)
    asset_ids = {position["assetId"] for position in positions if _is_scoreable_asset(position)}
    return {"assets": list_scores(db, asset_ids=asset_ids), "scope": "portfolio"}


@router.get("/dividends")
def dividends_radar(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    positions = get_positions(db, user.id)
    asset_ids = {position["assetId"] for position in positions if _is_scoreable_asset(position)}
    rows = sorted(list_scores(db, asset_ids=asset_ids), key=lambda item: item["scoreDividendos"], reverse=True)
    return {"assets": rows, "scope": "portfolio"}


@router.get("/growth")
def growth_radar(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    positions = get_positions(db, user.id)
    asset_ids = {position["assetId"] for position in positions if _is_scoreable_asset(position)}
    rows = sorted(list_scores(db, asset_ids=asset_ids), key=lambda item: item["scoreCrescimento"], reverse=True)
    return {"assets": rows, "scope": "portfolio"}
