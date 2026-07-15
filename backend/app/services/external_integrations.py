from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import ExternalIntegrationSnapshot, User


TRADING_DESK_INTEGRATION_KEY = "trading_desk_ev_plus"


def decimal_value(value: Any, digits: str = "0.01") -> Decimal:
    try:
        if value is None:
            return Decimal("0").quantize(Decimal(digits))
        if isinstance(value, str):
            value = value.replace("R$", "").replace("%", "").strip()
            if "," in value and "." in value:
                value = value.replace(".", "").replace(",", ".")
            elif "," in value:
                value = value.replace(",", ".")
        return Decimal(str(value)).quantize(Decimal(digits))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0").quantize(Decimal(digits))


def resolve_snapshot_user_id(db: Session, *, owner_email: str = "") -> str | None:
    email = owner_email.strip().lower()
    if not email:
        return None
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    return user.id if user else None


def save_external_integration_snapshot(
    db: Session,
    *,
    integration_key: str,
    payload: dict[str, Any],
    user_id: str | None = None,
    provider: str = "",
    status: str = "received",
    metadata: dict[str, Any] | None = None,
) -> ExternalIntegrationSnapshot:
    total_pnl = decimal_value(payload.get("totalPnl"))
    realized_pnl = decimal_value(payload.get("realizedPnl"))
    open_pnl = decimal_value(payload.get("openPnl"))
    if total_pnl == 0 and (realized_pnl or open_pnl):
        total_pnl = decimal_value(realized_pnl + open_pnl)

    initial_capital = decimal_value(payload.get("initialCapital"))
    current_balance = decimal_value(payload.get("currentBalance"))
    if current_balance == 0 and (initial_capital or total_pnl):
        current_balance = decimal_value(initial_capital + total_pnl)

    total_pnl_pct = decimal_value(payload.get("totalPnlPct"), "0.0001")
    if total_pnl_pct == 0 and initial_capital:
        total_pnl_pct = decimal_value((total_pnl / initial_capital) * Decimal("100"), "0.0001")

    snapshot = ExternalIntegrationSnapshot(
        user_id=user_id,
        integration_key=integration_key,
        provider=provider or str(payload.get("source") or integration_key),
        name=str(payload.get("name") or integration_key),
        status=status,
        currency=str(payload.get("currency") or "BRL")[:8],
        current_balance=current_balance,
        initial_capital=initial_capital,
        realized_pnl=realized_pnl,
        open_pnl=open_pnl,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        source_payload_json=json.dumps(payload, ensure_ascii=False, default=str),
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False, default=str),
        observed_at=parse_datetime(payload.get("updatedAt")) or datetime.now(UTC),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def get_latest_external_integration_snapshot(
    db: Session,
    *,
    integration_key: str,
    user_id: str | None = None,
) -> ExternalIntegrationSnapshot | None:
    conditions = [ExternalIntegrationSnapshot.integration_key == integration_key]
    if user_id:
        conditions.append(or_(ExternalIntegrationSnapshot.user_id == user_id, ExternalIntegrationSnapshot.user_id.is_(None)))
    stmt = (
        select(ExternalIntegrationSnapshot)
        .where(*conditions)
        .order_by(
            ExternalIntegrationSnapshot.observed_at.desc().nullslast(),
            ExternalIntegrationSnapshot.created_at.desc(),
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def trading_desk_summary_from_snapshot(snapshot: ExternalIntegrationSnapshot) -> dict[str, Any]:
    observed_at = snapshot.observed_at or snapshot.created_at
    updated_at = observed_at.isoformat() if observed_at else datetime.now(UTC).isoformat()
    return {
        "enabled": True,
        "connected": True,
        "status": "snapshot",
        "message": f"Ultimo saldo salvo no Supabase em {format_datetime_br(observed_at)}.",
        "source": snapshot.provider or TRADING_DESK_INTEGRATION_KEY,
        "name": snapshot.name or "Trading Desk EV+",
        "currency": snapshot.currency or "BRL",
        "currentBalance": float(snapshot.current_balance or 0),
        "initialCapital": float(snapshot.initial_capital or 0),
        "realizedPnl": float(snapshot.realized_pnl or 0),
        "openPnl": float(snapshot.open_pnl or 0),
        "totalPnl": float(snapshot.total_pnl or 0),
        "totalPnlPct": float(snapshot.total_pnl_pct or 0),
        "updatedAt": updated_at,
    }


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        text = str(value).strip().replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def format_datetime_br(value: datetime | None) -> str:
    if value is None:
        return "data nao informada"
    try:
        local = value.astimezone()
    except ValueError:
        local = value
    return local.strftime("%d/%m/%Y %H:%M")
