from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import SessionLocal
from app.models import AuditEvent


def write_audit_event(
    db: Session,
    *,
    event_type: str,
    category: str,
    action: str,
    message: str,
    user_id: str | None = None,
    actor_type: str = "user",
    severity: str = "info",
    resource_type: str = "",
    resource_id: str = "",
    request_id: str = "",
    ip_address: str = "",
    user_agent: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditEvent | None:
    if not get_settings().audit_enabled:
        return None
    event = AuditEvent(
        user_id=user_id,
        actor_type=actor_type,
        event_type=event_type,
        category=category,
        severity=severity,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        ip_address=ip_address[:80],
        user_agent=user_agent[:240],
        message=message,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False, default=str),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def write_audit_event_best_effort(**kwargs) -> None:
    try:
        db = SessionLocal()
        try:
            write_audit_event(db, **kwargs)
        finally:
            db.close()
    except Exception:
        # Auditoria nunca pode derrubar request de usuario.
        return


def list_audit_events(db: Session, *, user_id: str, limit: int = 100) -> list[AuditEvent]:
    stmt = (
        select(AuditEvent)
        .where((AuditEvent.user_id == user_id) | (AuditEvent.actor_type == "system"))
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def audit_summary(db: Session, *, user_id: str) -> dict:
    visible = (AuditEvent.user_id == user_id) | (AuditEvent.actor_type == "system")
    total = db.execute(select(func.count()).select_from(AuditEvent).where(visible)).scalar_one()
    critical = db.execute(select(func.count()).select_from(AuditEvent).where(visible, AuditEvent.severity == "critical")).scalar_one()
    warnings = db.execute(select(func.count()).select_from(AuditEvent).where(visible, AuditEvent.severity == "warning")).scalar_one()
    return {"total": total, "critical": critical, "warnings": warnings}


def purge_old_audit_events(db: Session, *, retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    result = db.execute(delete(AuditEvent).where(AuditEvent.created_at < cutoff))
    db.commit()
    return int(result.rowcount or 0)


def audit_event_to_dict(event: AuditEvent) -> dict:
    try:
        metadata = json.loads(event.metadata_json or "{}")
    except json.JSONDecodeError:
        metadata = {}
    return {
        "id": event.id,
        "userId": event.user_id,
        "actorType": event.actor_type,
        "eventType": event.event_type,
        "category": event.category,
        "severity": event.severity,
        "action": event.action,
        "resourceType": event.resource_type,
        "resourceId": event.resource_id,
        "requestId": event.request_id,
        "message": event.message,
        "metadata": metadata,
        "createdAt": event.created_at.isoformat() if event.created_at else "",
    }
