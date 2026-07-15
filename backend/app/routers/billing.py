from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.billing.gateway import (
    BillingGatewayError,
    checkout_session_to_dict,
    create_checkout_session,
    list_user_billing,
    process_mock_checkout_success,
    process_provider_webhook,
    webhook_event_to_dict,
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models import BillingCheckoutSession, BillingWebhookEvent, User
from app.services.rbac import ADMIN_ROLES, require_any_role


router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutSessionRequest(BaseModel):
    plan_code: str = Field(default="alpha_premium", max_length=80)
    billing_cycle: str = Field(default="monthly", max_length=24)
    success_url: str = Field(default="", max_length=1000)
    cancel_url: str = Field(default="", max_length=1000)
    idempotency_key: str = Field(default="", max_length=160)


@router.post("/checkout/sessions", status_code=status.HTTP_201_CREATED)
def create_billing_checkout_session(
    payload: CheckoutSessionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return create_checkout_session(
            db,
            user=user,
            plan_code=payload.plan_code,
            billing_cycle=payload.billing_cycle,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
            idempotency_key=payload.idempotency_key,
            commit=True,
        )
    except BillingGatewayError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/mock/checkout/{session_id}/success")
def confirm_mock_checkout(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = process_mock_checkout_success(db, session_id=session_id, user_id=user.id, commit=True)
    except BillingGatewayError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return result


@router.post("/webhooks/{provider}")
async def billing_webhook(
    provider: str,
    request: Request,
    x_billing_signature: str = Header(default=""),
    db: Session = Depends(get_db),
):
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload JSON invalido.") from exc
    try:
        return process_provider_webhook(
            db,
            provider=provider,
            payload=payload,
            signature_header=x_billing_signature,
            commit=True,
        )
    except BillingGatewayError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/me")
def get_my_billing(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_user_billing(db, user_id=user.id)


@router.get("/checkout/sessions/{session_id}")
def get_checkout_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(BillingCheckoutSession, session_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout nao encontrado.")
    return checkout_session_to_dict(row)


@router.get("/admin/webhook-events")
def list_billing_webhook_events(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_any_role(db, user_id=user.id, accepted_roles=ADMIN_ROLES)
    safe_limit = min(max(limit, 1), 300)
    rows = list(db.execute(select(BillingWebhookEvent).order_by(desc(BillingWebhookEvent.received_at)).limit(safe_limit)).scalars().all())
    return {"items": [webhook_event_to_dict(row) for row in rows], "count": len(rows), "limit": safe_limit}
