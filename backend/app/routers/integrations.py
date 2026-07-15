from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.audit import write_audit_event
from app.services.external_integrations import (
    TRADING_DESK_INTEGRATION_KEY,
    get_latest_external_integration_snapshot,
    resolve_snapshot_user_id,
    save_external_integration_snapshot,
    trading_desk_summary_from_snapshot,
)


router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/trading-desk/snapshot", status_code=status.HTTP_201_CREATED)
def receive_trading_desk_snapshot(
    payload: dict[str, Any],
    request: Request,
    x_integration_key: str | None = Header(default=None, alias="X-Integration-Key"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    expected_key = settings.trading_desk_integration_key.strip()
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TRADING_DESK_INTEGRATION_KEY nao configurada no backend.",
        )
    if not secrets.compare_digest(str(x_integration_key or ""), expected_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave de integracao invalida.")

    owner_email = str(payload.get("ownerEmail") or settings.trading_desk_snapshot_owner_email or "")
    user_id = resolve_snapshot_user_id(db, owner_email=owner_email)
    snapshot = save_external_integration_snapshot(
        db,
        integration_key=TRADING_DESK_INTEGRATION_KEY,
        payload=payload,
        user_id=user_id,
        provider=str(payload.get("source") or TRADING_DESK_INTEGRATION_KEY),
        status="received",
        metadata={
            "remoteAddress": _client_ip(request),
            "userAgent": request.headers.get("user-agent", ""),
            "ownerEmail": owner_email,
        },
    )
    db.commit()
    db.refresh(snapshot)
    write_audit_event(
        db,
        user_id=user_id,
        actor_type="system",
        event_type="external_integration_snapshot_received",
        category="integration",
        severity="info",
        action="receive_trading_desk_snapshot",
        resource_type="external_integration_snapshot",
        resource_id=snapshot.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        message="Snapshot financeiro do Trading Desk EV+ recebido e salvo.",
        metadata={
            "integrationKey": TRADING_DESK_INTEGRATION_KEY,
            "currentBalance": float(snapshot.current_balance or 0),
            "totalPnl": float(snapshot.total_pnl or 0),
            "observedAt": snapshot.observed_at.isoformat() if snapshot.observed_at else "",
        },
    )
    return {
        "ok": True,
        "id": snapshot.id,
        "integrationKey": snapshot.integration_key,
        "currentBalance": float(snapshot.current_balance or 0),
        "updatedAt": snapshot.observed_at.isoformat() if snapshot.observed_at else "",
    }


@router.get("/trading-desk/snapshot")
def latest_trading_desk_snapshot(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    snapshot = get_latest_external_integration_snapshot(
        db,
        integration_key=TRADING_DESK_INTEGRATION_KEY,
        user_id=user.id,
    )
    if snapshot is None:
        return {"connected": False, "status": "empty", "message": "Nenhum snapshot do Trading Desk EV+ foi recebido ainda."}
    return trading_desk_summary_from_snapshot(snapshot)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
