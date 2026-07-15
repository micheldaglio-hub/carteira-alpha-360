from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Iterable

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import User, UserRole


ADMIN_ROLE = "admin"
EDITOR_ROLE = "editor"
REVIEWER_ROLE = "reviewer"
PREMIUM_SUBSCRIBER_ROLE = "premium_subscriber"
FREE_USER_ROLE = "free_user"

ADMIN_ROLES = {ADMIN_ROLE}
EDITORIAL_ROLES = {ADMIN_ROLE, EDITOR_ROLE, REVIEWER_ROLE}
PUBLISHER_ROLES = {ADMIN_ROLE, EDITOR_ROLE}
REVIEW_ROLES = {ADMIN_ROLE, REVIEWER_ROLE}
APPROVAL_ROLES = {ADMIN_ROLE, EDITOR_ROLE}
SUBSCRIBER_ROLES = {ADMIN_ROLE, EDITOR_ROLE, REVIEWER_ROLE, PREMIUM_SUBSCRIBER_ROLE}

ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    ADMIN_ROLE: {
        "label": "Administrador",
        "description": "Controle total da vertical premium, RBAC, publicacoes, revisoes e assinaturas.",
        "permissions": [
            "premium.admin",
            "premium.publication.write",
            "premium.publication.review",
            "premium.publication.approve",
            "premium.subscription.manage",
            "premium.download",
        ],
    },
    EDITOR_ROLE: {
        "label": "Editor",
        "description": "Cria rascunhos, executa motores editoriais, gera snapshots, HTML e PDF.",
        "permissions": [
            "premium.publication.write",
            "premium.publication.approve",
            "premium.download",
        ],
    },
    REVIEWER_ROLE: {
        "label": "Revisor",
        "description": "Revisa edicoes premium antes da aprovacao final.",
        "permissions": [
            "premium.publication.review",
            "premium.download",
        ],
    },
    PREMIUM_SUBSCRIBER_ROLE: {
        "label": "Assinante Premium",
        "description": "Acessa area premium e edicoes liberadas conforme assinatura ativa.",
        "permissions": [
            "premium.subscriber.read",
        ],
    },
    FREE_USER_ROLE: {
        "label": "Usuario Free",
        "description": "Acesso basico ao sistema e preview institucional.",
        "permissions": [
            "premium.preview",
        ],
    },
}


def normalize_role(role: str) -> str:
    return str(role or "").strip().lower()


def valid_roles() -> list[str]:
    return list(ROLE_DEFINITIONS.keys())


def grant_role_to_user(
    db: Session,
    *,
    user_id: str,
    role: str,
    scope_type: str = "global",
    scope_id: str = "*",
    status_value: str = "active",
    source: str = "manual",
    granted_by_user_id: str | None = None,
    starts_at: datetime | None = None,
    expires_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> UserRole:
    normalized = normalize_role(role)
    if normalized not in ROLE_DEFINITIONS:
        raise ValueError(f"Papel RBAC invalido: {role}")

    row = db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role == normalized,
            UserRole.scope_type == scope_type,
            UserRole.scope_id == scope_id,
        )
    ).scalar_one_or_none()
    if row is None:
        row = UserRole(user_id=user_id, role=normalized, scope_type=scope_type, scope_id=scope_id)
        db.add(row)
    row.status = status_value[:32]
    row.source = source[:80]
    row.granted_by_user_id = granted_by_user_id
    row.starts_at = starts_at
    row.expires_at = expires_at
    row.metadata_json = _json(metadata or {})
    row.updated_at = datetime.now(UTC)
    db.flush()
    if commit:
        db.commit()
        db.refresh(row)
    return row


def ensure_default_user_role(db: Session, *, user_id: str, commit: bool = True) -> UserRole | None:
    existing = list_user_roles(db, user_id=user_id, active_only=False)
    if existing:
        return None
    return grant_role_to_user(
        db,
        user_id=user_id,
        role=FREE_USER_ROLE,
        source="auth_default",
        metadata={"reason": "new_user_default_role"},
        commit=commit,
    )


def list_user_roles(db: Session, *, user_id: str, active_only: bool = True) -> list[UserRole]:
    stmt = select(UserRole).where(UserRole.user_id == user_id).order_by(UserRole.role)
    if active_only:
        now = datetime.now(UTC)
        stmt = stmt.where(
            UserRole.status == "active",
            or_(UserRole.starts_at.is_(None), UserRole.starts_at <= now),
            or_(UserRole.expires_at.is_(None), UserRole.expires_at >= now),
        )
    return list(db.execute(stmt).scalars().all())


def list_user_role_names(db: Session, *, user_id: str, active_only: bool = True) -> list[str]:
    return [row.role for row in list_user_roles(db, user_id=user_id, active_only=active_only)]


def user_has_any_role(db: Session, *, user_id: str, roles: Iterable[str]) -> bool:
    accepted = {normalize_role(role) for role in roles}
    if not accepted:
        return False
    return any(role in accepted for role in list_user_role_names(db, user_id=user_id))


def require_any_role(db: Session, user: User, roles: Iterable[str], *, detail: str | None = None) -> None:
    if user_has_any_role(db, user_id=user.id, roles=roles):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail or "Seu usuario nao possui permissao para executar esta acao.",
    )


def role_to_dict(row: UserRole) -> dict[str, Any]:
    definition = ROLE_DEFINITIONS.get(row.role, {})
    return {
        "id": row.id,
        "userId": row.user_id,
        "role": row.role,
        "label": definition.get("label", row.role),
        "description": definition.get("description", ""),
        "permissions": definition.get("permissions", []),
        "scopeType": row.scope_type,
        "scopeId": row.scope_id,
        "status": row.status,
        "source": row.source,
        "grantedByUserId": row.granted_by_user_id or "",
        "startsAt": row.starts_at.isoformat() if row.starts_at else "",
        "expiresAt": row.expires_at.isoformat() if row.expires_at else "",
        "metadata": _json_load(row.metadata_json, {}),
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def rbac_summary(db: Session, *, user_id: str) -> dict[str, Any]:
    roles = list_user_roles(db, user_id=user_id)
    role_names = [row.role for row in roles]
    permissions: set[str] = set()
    for role in role_names:
        permissions.update(ROLE_DEFINITIONS.get(role, {}).get("permissions", []))
    return {
        "roles": [role_to_dict(row) for row in roles],
        "roleNames": role_names,
        "permissions": sorted(permissions),
        "isAdmin": ADMIN_ROLE in role_names,
        "isEditorial": bool(set(role_names) & EDITORIAL_ROLES),
        "isSubscriber": bool(set(role_names) & SUBSCRIBER_ROLES),
        "definitions": ROLE_DEFINITIONS,
    }


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)


def _json_load(raw: str | None, default: Any = None) -> Any:
    if not raw:
        return {} if default is None else default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {} if default is None else default
