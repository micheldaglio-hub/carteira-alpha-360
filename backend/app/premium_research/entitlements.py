from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import (
    PremiumAccessLog,
    PremiumEntitlement,
    PublicationArtifact,
    SubscriptionPlan,
    UserSubscription,
)
from app.services.rbac import PREMIUM_SUBSCRIBER_ROLE, grant_role_to_user


ENTITLEMENT_ENGINE_VERSION = "2026.07.entitlements1"
DOWNLOAD_ACTION = "download_pdf"
READ_ACTION = "read_premium_artifact"

DEFAULT_PLAN_DEFINITIONS = [
    {
        "code": "alpha_free",
        "name": "Alpha Free",
        "tier": "free",
        "monthlyPrice": 0,
        "annualPrice": 0,
        "features": ["premium.research.preview"],
        "limits": {"pdfDownloadsPerPeriod": 0, "archiveMonths": 0},
    },
    {
        "code": "alpha_premium",
        "name": "Alpha Premium",
        "tier": "premium",
        "monthlyPrice": 97,
        "annualPrice": 970,
        "features": ["premium.research.read", "premium.pdf.download", "premium.publications.archive"],
        "limits": {"pdfDownloadsPerPeriod": 30, "archiveMonths": 24},
    },
    {
        "code": "alpha_institutional",
        "name": "Alpha Institutional",
        "tier": "institutional",
        "monthlyPrice": 497,
        "annualPrice": 4970,
        "features": [
            "premium.research.read",
            "premium.pdf.download",
            "premium.publications.archive",
            "premium.pdf.bulk_download",
            "premium.research.admin",
        ],
        "limits": {"pdfDownloadsPerPeriod": 500, "archiveMonths": 120},
    },
]

ACTION_ENTITLEMENTS = {
    DOWNLOAD_ACTION: {"premium.pdf.download", "premium.pdf.bulk_download", "premium.research.admin"},
    READ_ACTION: {"premium.research.read", "premium.research.admin"},
}


def seed_default_subscription_plans(db: Session, *, commit: bool = True) -> list[SubscriptionPlan]:
    plans: list[SubscriptionPlan] = []
    for definition in DEFAULT_PLAN_DEFINITIONS:
        plan = db.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == definition["code"])).scalar_one_or_none()
        if plan is None:
            plan = SubscriptionPlan(code=definition["code"], name=definition["name"])
            db.add(plan)
        plan.name = definition["name"]
        plan.status = "active"
        plan.tier = definition["tier"]
        plan.currency = "BRL"
        plan.monthly_price = Decimal(str(definition["monthlyPrice"]))
        plan.annual_price = Decimal(str(definition["annualPrice"]))
        plan.features_json = _json(definition["features"])
        plan.limits_json = _json(definition["limits"])
        plan.metadata_json = _json({"engineVersion": ENTITLEMENT_ENGINE_VERSION, "seeded": True})
        plans.append(plan)
    db.flush()
    if commit:
        db.commit()
        for plan in plans:
            db.refresh(plan)
    return plans


def grant_subscription_to_user(
    db: Session,
    *,
    user_id: str,
    plan_code: str,
    status: str = "active",
    period_days: int = 30,
    billing_provider: str = "manual",
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    seed_default_subscription_plans(db, commit=False)
    plan = db.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code)).scalar_one_or_none()
    if plan is None:
        raise ValueError("Plano premium nao encontrado.")

    now = datetime.now(UTC)
    period_end = now + timedelta(days=max(1, period_days))
    subscription = db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.plan_id == plan.id,
            UserSubscription.status.in_(("active", "trialing")),
        )
    ).scalar_one_or_none()
    if subscription is None:
        subscription = UserSubscription(user_id=user_id, plan_id=plan.id, plan_code=plan.code)
        db.add(subscription)
    subscription.status = status[:32]
    subscription.plan_code = plan.code
    subscription.billing_provider = billing_provider[:80]
    subscription.current_period_start = now
    subscription.current_period_end = period_end
    subscription.metadata_json = _json(metadata or {"engineVersion": ENTITLEMENT_ENGINE_VERSION})
    db.flush()

    entitlements = _sync_entitlements_for_subscription(db, subscription, plan, starts_at=now, expires_at=period_end)
    if status in {"active", "trialing"}:
        grant_role_to_user(
            db,
            user_id=user_id,
            role=PREMIUM_SUBSCRIBER_ROLE,
            source="subscription",
            starts_at=now,
            expires_at=period_end,
            metadata={"planCode": plan.code, "subscriptionId": subscription.id, "engineVersion": ENTITLEMENT_ENGINE_VERSION},
            commit=False,
        )
    if commit:
        db.commit()
        db.refresh(subscription)
        for entitlement in entitlements:
            db.refresh(entitlement)
    return {
        "subscription": subscription_to_dict(subscription),
        "plan": plan_to_dict(plan),
        "entitlements": [entitlement_to_dict(row) for row in entitlements],
    }


def list_user_premium_access(db: Session, *, user_id: str) -> dict[str, Any]:
    seed_default_subscription_plans(db, commit=False)
    subscriptions = list(
        db.execute(
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .order_by(UserSubscription.created_at.desc())
        )
        .scalars()
        .all()
    )
    entitlements = list(
        db.execute(
            select(PremiumEntitlement)
            .where(PremiumEntitlement.user_id == user_id)
            .order_by(PremiumEntitlement.created_at.desc())
        )
        .scalars()
        .all()
    )
    return {
        "subscriptions": [subscription_to_dict(row) for row in subscriptions],
        "entitlements": [entitlement_to_dict(row) for row in entitlements],
        "activeEntitlements": [entitlement_to_dict(row) for row in _active_entitlements(db, user_id=user_id)],
    }


def authorize_premium_artifact_access(
    db: Session,
    *,
    user_id: str,
    artifact: PublicationArtifact,
    action: str,
    editorial_owner: bool = False,
    ip_address: str = "",
    user_agent: str = "",
    commit: bool = True,
) -> dict[str, Any]:
    inspection = inspect_premium_artifact_access(
        db,
        user_id=user_id,
        artifact=artifact,
        action=action,
        editorial_owner=editorial_owner,
    )
    if inspection["allowed"] and inspection["reason"] == "editorial_owner_access":
        log = _record_access_log(
            db,
            user_id=user_id,
            artifact=artifact,
            action=action,
            allowed=True,
            reason="editorial_owner_access",
            entitlement=None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if commit:
            db.commit()
            db.refresh(log)
        return {"allowed": True, "reason": "editorial_owner_access", "entitlement": None, "accessLogId": log.id}

    if not inspection["allowed"] and inspection["reason"] == "missing_active_entitlement":
        log = _record_access_log(
            db,
            user_id=user_id,
            artifact=artifact,
            action=action,
            allowed=False,
            reason="missing_active_entitlement",
            entitlement=None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if commit:
            db.commit()
            db.refresh(log)
        return {"allowed": False, "reason": "missing_active_entitlement", "entitlement": None, "accessLogId": log.id}

    entitlement = inspection.get("entitlementModel")
    if entitlement is None:
        log = _record_access_log(
            db,
            user_id=user_id,
            artifact=artifact,
            action=action,
            allowed=False,
            reason="missing_active_entitlement",
            entitlement=None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if commit:
            db.commit()
            db.refresh(log)
        return {"allowed": False, "reason": "missing_active_entitlement", "entitlement": None, "accessLogId": log.id}

    if entitlement.usage_limit and entitlement.usage_count >= entitlement.usage_limit:
        log = _record_access_log(
            db,
            user_id=user_id,
            artifact=artifact,
            action=action,
            allowed=False,
            reason="entitlement_usage_limit_reached",
            entitlement=entitlement,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if commit:
            db.commit()
            db.refresh(log)
        return {
            "allowed": False,
            "reason": "entitlement_usage_limit_reached",
            "entitlement": entitlement_to_dict(entitlement),
            "accessLogId": log.id,
        }

    entitlement.usage_count += 1
    log = _record_access_log(
        db,
        user_id=user_id,
        artifact=artifact,
        action=action,
        allowed=True,
        reason="active_entitlement",
        entitlement=entitlement,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if commit:
        db.commit()
        db.refresh(entitlement)
        db.refresh(log)
    return {"allowed": True, "reason": "active_entitlement", "entitlement": entitlement_to_dict(entitlement), "accessLogId": log.id}


def inspect_premium_artifact_access(
    db: Session,
    *,
    user_id: str,
    artifact: PublicationArtifact,
    action: str,
    editorial_owner: bool = False,
) -> dict[str, Any]:
    if editorial_owner:
        return {"allowed": True, "reason": "editorial_owner_access", "entitlement": None, "entitlementModel": None}
    entitlement = _matching_entitlement(db, user_id=user_id, artifact=artifact, action=action)
    if entitlement is None:
        return {"allowed": False, "reason": "missing_active_entitlement", "entitlement": None, "entitlementModel": None}
    if entitlement.usage_limit and entitlement.usage_count >= entitlement.usage_limit:
        return {
            "allowed": False,
            "reason": "entitlement_usage_limit_reached",
            "entitlement": entitlement_to_dict(entitlement),
            "entitlementModel": entitlement,
        }
    return {
        "allowed": True,
        "reason": "active_entitlement",
        "entitlement": entitlement_to_dict(entitlement),
        "entitlementModel": entitlement,
    }


def list_premium_access_logs(db: Session, *, user_id: str, limit: int = 100) -> dict[str, Any]:
    rows = list(
        db.execute(
            select(PremiumAccessLog)
            .where(PremiumAccessLog.user_id == user_id)
            .order_by(PremiumAccessLog.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return {"items": [access_log_to_dict(row) for row in rows], "count": len(rows), "limit": limit}


def plan_to_dict(plan: SubscriptionPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "code": plan.code,
        "name": plan.name,
        "status": plan.status,
        "tier": plan.tier,
        "currency": plan.currency,
        "monthlyPrice": _number(plan.monthly_price),
        "annualPrice": _number(plan.annual_price),
        "features": _json_load(plan.features_json, []),
        "limits": _json_load(plan.limits_json, {}),
        "metadata": _json_load(plan.metadata_json, {}),
        "createdAt": plan.created_at.isoformat() if plan.created_at else "",
    }


def subscription_to_dict(subscription: UserSubscription) -> dict[str, Any]:
    return {
        "id": subscription.id,
        "userId": subscription.user_id,
        "planId": subscription.plan_id,
        "planCode": subscription.plan_code,
        "status": subscription.status,
        "billingProvider": subscription.billing_provider,
        "externalSubscriptionId": subscription.external_subscription_id,
        "currentPeriodStart": subscription.current_period_start.isoformat() if subscription.current_period_start else "",
        "currentPeriodEnd": subscription.current_period_end.isoformat() if subscription.current_period_end else "",
        "startedAt": subscription.started_at.isoformat() if subscription.started_at else "",
        "canceledAt": subscription.canceled_at.isoformat() if subscription.canceled_at else "",
        "metadata": _json_load(subscription.metadata_json, {}),
        "createdAt": subscription.created_at.isoformat() if subscription.created_at else "",
    }


def entitlement_to_dict(entitlement: PremiumEntitlement) -> dict[str, Any]:
    return {
        "id": entitlement.id,
        "userId": entitlement.user_id,
        "subscriptionId": entitlement.subscription_id or "",
        "planId": entitlement.plan_id or "",
        "entitlementKey": entitlement.entitlement_key,
        "scopeType": entitlement.scope_type,
        "scopeId": entitlement.scope_id,
        "status": entitlement.status,
        "source": entitlement.source,
        "startsAt": entitlement.starts_at.isoformat() if entitlement.starts_at else "",
        "expiresAt": entitlement.expires_at.isoformat() if entitlement.expires_at else "",
        "usageLimit": entitlement.usage_limit,
        "usageCount": entitlement.usage_count,
        "metadata": _json_load(entitlement.metadata_json, {}),
        "createdAt": entitlement.created_at.isoformat() if entitlement.created_at else "",
    }


def access_log_to_dict(row: PremiumAccessLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "userId": row.user_id,
        "publicationId": row.publication_id or "",
        "artifactId": row.artifact_id or "",
        "snapshotId": row.snapshot_id or "",
        "entitlementId": row.entitlement_id or "",
        "action": row.action,
        "allowed": row.allowed,
        "reason": row.reason,
        "entitlementKey": row.entitlement_key,
        "artifactHash": row.artifact_hash,
        "metadata": _json_load(row.metadata_json, {}),
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def _sync_entitlements_for_subscription(
    db: Session,
    subscription: UserSubscription,
    plan: SubscriptionPlan,
    *,
    starts_at: datetime,
    expires_at: datetime,
) -> list[PremiumEntitlement]:
    features = list(_json_load(plan.features_json, []))
    limits = _json_load(plan.limits_json, {})
    entitlements: list[PremiumEntitlement] = []
    for key in features:
        entitlement = db.execute(
            select(PremiumEntitlement).where(
                PremiumEntitlement.user_id == subscription.user_id,
                PremiumEntitlement.subscription_id == subscription.id,
                PremiumEntitlement.entitlement_key == str(key),
                PremiumEntitlement.scope_type == "global",
                PremiumEntitlement.scope_id == "*",
            )
        ).scalar_one_or_none()
        if entitlement is None:
            entitlement = PremiumEntitlement(
                user_id=subscription.user_id,
                subscription_id=subscription.id,
                plan_id=plan.id,
                entitlement_key=str(key),
                scope_type="global",
                scope_id="*",
            )
            db.add(entitlement)
        entitlement.status = "active"
        entitlement.source = "subscription"
        entitlement.starts_at = starts_at
        entitlement.expires_at = expires_at
        entitlement.usage_limit = int(limits.get("pdfDownloadsPerPeriod", 0) or 0) if str(key) in ACTION_ENTITLEMENTS[DOWNLOAD_ACTION] else 0
        entitlement.metadata_json = _json({"planCode": plan.code, "engineVersion": ENTITLEMENT_ENGINE_VERSION})
        entitlements.append(entitlement)
    db.flush()
    return entitlements


def _active_entitlements(db: Session, *, user_id: str) -> list[PremiumEntitlement]:
    now = datetime.now(UTC)
    return list(
        db.execute(
            select(PremiumEntitlement).where(
                PremiumEntitlement.user_id == user_id,
                PremiumEntitlement.status == "active",
                or_(PremiumEntitlement.starts_at.is_(None), PremiumEntitlement.starts_at <= now),
                or_(PremiumEntitlement.expires_at.is_(None), PremiumEntitlement.expires_at >= now),
            )
        )
        .scalars()
        .all()
    )


def _matching_entitlement(
    db: Session,
    *,
    user_id: str,
    artifact: PublicationArtifact,
    action: str,
) -> PremiumEntitlement | None:
    accepted = ACTION_ENTITLEMENTS.get(action, {action})
    for entitlement in _active_entitlements(db, user_id=user_id):
        if entitlement.entitlement_key not in accepted:
            continue
        if _scope_matches(entitlement, artifact):
            return entitlement
    return None


def _scope_matches(entitlement: PremiumEntitlement, artifact: PublicationArtifact) -> bool:
    if entitlement.scope_type == "global" and entitlement.scope_id == "*":
        return True
    if entitlement.scope_type == "publication" and entitlement.scope_id == artifact.publication_id:
        return True
    if entitlement.scope_type == "artifact" and entitlement.scope_id == artifact.id:
        return True
    if entitlement.scope_type == "snapshot" and entitlement.scope_id == artifact.snapshot_id:
        return True
    return False


def _record_access_log(
    db: Session,
    *,
    user_id: str,
    artifact: PublicationArtifact,
    action: str,
    allowed: bool,
    reason: str,
    entitlement: PremiumEntitlement | None,
    ip_address: str = "",
    user_agent: str = "",
) -> PremiumAccessLog:
    row = PremiumAccessLog(
        user_id=user_id,
        publication_id=artifact.publication_id,
        artifact_id=artifact.id,
        snapshot_id=artifact.snapshot_id,
        entitlement_id=entitlement.id if entitlement else None,
        action=action,
        allowed=allowed,
        reason=reason,
        entitlement_key=entitlement.entitlement_key if entitlement else "",
        artifact_hash=artifact.artifact_hash,
        ip_address=ip_address[:80],
        user_agent=user_agent[:240],
        metadata_json=_json(
            {
                "artifactType": artifact.artifact_type,
                "contentType": artifact.content_type,
                "engineVersion": ENTITLEMENT_ENGINE_VERSION,
            }
        ),
    )
    db.add(row)
    db.flush()
    return row


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=_json_default)


def _json_load(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
