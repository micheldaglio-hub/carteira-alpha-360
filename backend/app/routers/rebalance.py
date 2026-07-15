from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.rebalance import get_rebalance_plan


router = APIRouter(prefix="/rebalance", tags=["rebalance"])


@router.get("")
def rebalance(
    next_contribution: float = Query(default=2500, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_rebalance_plan(db, user.id, next_contribution=next_contribution)
