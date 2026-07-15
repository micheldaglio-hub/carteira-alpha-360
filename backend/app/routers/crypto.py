from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import CryptoTransactionCreate
from app.services.crypto import get_crypto_dashboard, register_crypto_transaction, sync_user_crypto


router = APIRouter(prefix="/crypto", tags=["crypto"])


@router.get("")
def crypto_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_crypto_dashboard(db, user.id)


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def create_crypto_transaction(
    payload: CryptoTransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return register_crypto_transaction(db, user.id, payload)


@router.post("/sync-market")
def sync_crypto_market(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return sync_user_crypto(db, user.id)
