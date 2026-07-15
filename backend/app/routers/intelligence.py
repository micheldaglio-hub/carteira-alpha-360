from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.alpha.intelligence_service import get_alpha_scores, get_copilot, get_health, get_insights, get_summary, get_timeline
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User


router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_summary(db, user.id)


@router.get("/timeline")
def timeline(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_timeline(db, user.id)


@router.get("/health")
def health(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_health(db, user.id)


@router.get("/insights")
def insights(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_insights(db, user.id)


@router.get("/alpha-score")
def alpha_score(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_alpha_scores(db, user.id)


@router.get("/copilot")
def copilot(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_copilot(db, user.id)
