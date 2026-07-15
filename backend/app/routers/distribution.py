from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.distribution.engine import (
    DistributionEngineError,
    campaign_to_dict,
    create_distribution_campaign,
    dispatch_distribution_campaign,
    list_distribution_campaigns,
    process_distribution_webhook,
)
from app.models import DistributionCampaign, User
from app.services.rbac import PUBLISHER_ROLES, require_any_role


router = APIRouter(prefix="/distribution", tags=["distribution"])


class DistributionCampaignRequest(BaseModel):
    publication_id: str = Field(max_length=32)
    artifact_id: str | None = Field(default=None, max_length=32)
    channel: str = Field(default="email", max_length=40)
    audience_type: str = Field(default="premium_subscribers", max_length=80)
    subject: str = Field(default="", max_length=220)
    preview_text: str = Field(default="", max_length=1000)
    manual_user_ids: list[str] = Field(default_factory=list)


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: DistributionCampaignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_any_role(db, user, PUBLISHER_ROLES)
    try:
        return create_distribution_campaign(
            db,
            publication_id=payload.publication_id,
            artifact_id=payload.artifact_id,
            created_by_user_id=user.id,
            channel=payload.channel,
            audience_type=payload.audience_type,
            subject=payload.subject,
            preview_text=payload.preview_text,
            manual_user_ids=payload.manual_user_ids,
            commit=True,
        )
    except DistributionEngineError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/dispatch")
def dispatch_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_any_role(db, user, PUBLISHER_ROLES)
    try:
        return dispatch_distribution_campaign(db, campaign_id=campaign_id, actor_user_id=user.id, commit=True)
    except DistributionEngineError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/campaigns")
def list_campaigns(
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_any_role(db, user, PUBLISHER_ROLES)
    return list_distribution_campaigns(db, limit=limit)


@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: str,
    include_events: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_any_role(db, user, PUBLISHER_ROLES)
    campaign = db.get(DistributionCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campanha nao encontrada.")
    return campaign_to_dict(campaign, include_recipients=True, include_events=include_events)


@router.post("/webhooks/{provider}")
async def distribution_webhook(
    provider: str,
    request: Request,
    x_distribution_signature: str = Header(default=""),
    db: Session = Depends(get_db),
):
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload JSON invalido.") from exc
    try:
        return process_distribution_webhook(
            db,
            provider=provider,
            payload=payload,
            signature_header=x_distribution_signature,
            commit=True,
        )
    except DistributionEngineError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
