from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    DistributionCampaign,
    DistributionEventLog,
    DistributionRecipient,
    PremiumEntitlement,
    PublicationArtifact,
    ResearchPublication,
    User,
)
from app.premium_research.renderer import artifact_to_dict
from app.services.audit import write_audit_event

from .providers import DistributionSendResult, get_distribution_provider, resolve_distribution_provider


DISTRIBUTION_ENGINE_VERSION = "2026.07.distribution1"
READ_ENTITLEMENTS = {"premium.research.read", "premium.research.admin"}
DOWNLOAD_ENTITLEMENTS = {"premium.pdf.download", "premium.pdf.bulk_download", "premium.research.admin"}
SUPPORTED_CHANNELS = {"email", "in_app", "webhook"}
SUPPORTED_AUDIENCES = {"premium_subscribers", "manual_user", "test_user"}


class DistributionEngineError(ValueError):
    pass


def create_distribution_campaign(
    db: Session,
    *,
    publication_id: str,
    artifact_id: str | None,
    created_by_user_id: str,
    channel: str = "email",
    audience_type: str = "premium_subscribers",
    subject: str = "",
    preview_text: str = "",
    manual_user_ids: list[str] | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    publication = db.get(ResearchPublication, publication_id)
    if publication is None:
        raise DistributionEngineError("Publicacao premium nao encontrada.")
    if publication.status not in {"approved", "published"}:
        raise DistributionEngineError("Distribuicao exige publicacao aprovada ou publicada.")
    channel = _normalize_channel(channel)
    audience_type = _normalize_audience(audience_type)
    artifact = _resolve_artifact(db, publication=publication, artifact_id=artifact_id)
    if artifact and artifact.publication_id != publication.id:
        raise DistributionEngineError("Artefato nao pertence a publicacao informada.")

    recipients = _resolve_recipients(db, audience_type=audience_type, manual_user_ids=manual_user_ids or [])
    provider_choice = resolve_distribution_provider()
    provider = provider_choice.name
    campaign = DistributionCampaign(
        publication_id=publication.id,
        artifact_id=artifact.id if artifact else None,
        created_by_user_id=created_by_user_id,
        name=f"{publication.period} - {publication.title}"[:220],
        channel=channel,
        audience_type=audience_type,
        provider=provider,
        provider_campaign_id=f"{provider}_campaign_{publication.id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"[:160],
        status="ready",
        subject=(subject or publication.title or "Carteira Alpha Premium")[:220],
        preview_text=preview_text or publication.subtitle or "Nova edicao premium disponivel para assinantes.",
        recipient_count=len(recipients),
        payload_json=_json(_distribution_payload(publication, artifact)),
        metadata_json=_json(
            {
                "engineVersion": DISTRIBUTION_ENGINE_VERSION,
                "artifactHash": artifact.artifact_hash if artifact else "",
                "publicationStatus": publication.status,
                "providerMode": "test" if provider == "mock" else "external",
                "configuredProvider": provider_choice.configured_name,
                "fallbackReason": provider_choice.fallback_reason,
            }
        ),
    )
    db.add(campaign)
    db.flush()
    for row in recipients:
        recipient = DistributionRecipient(
            campaign_id=campaign.id,
            user_id=row["userId"],
            email=row["email"],
            full_name=row["fullName"],
            status="queued",
            entitlement_status=row["entitlementStatus"],
            metadata_json=_json({"source": row["source"], "engineVersion": DISTRIBUTION_ENGINE_VERSION}),
        )
        db.add(recipient)
    db.flush()
    _audit(
        db,
        user_id=created_by_user_id,
        action="distribution_campaign_created",
        message=f"Campanha de distribuicao criada para {campaign.recipient_count} destinatario(s).",
        resource_id=campaign.id,
        metadata={"publicationId": publication.id, "artifactId": artifact.id if artifact else "", "channel": channel, "audienceType": audience_type},
    )
    if commit:
        db.commit()
        db.refresh(campaign)
    return campaign_to_dict(campaign, include_recipients=True)


def dispatch_distribution_campaign(
    db: Session,
    *,
    campaign_id: str,
    actor_user_id: str,
    commit: bool = True,
) -> dict[str, Any]:
    campaign = db.get(DistributionCampaign, campaign_id)
    if campaign is None:
        raise DistributionEngineError("Campanha nao encontrada.")
    if campaign.status in {"sent", "completed"}:
        return campaign_to_dict(campaign, include_recipients=True)
    if campaign.status not in {"ready", "queued", "failed"}:
        raise DistributionEngineError("Campanha nao esta pronta para envio.")

    now = datetime.now(UTC)
    campaign.status = "sending"
    campaign.dispatched_at = now
    delivered = 0
    failed = 0
    skipped = 0
    for recipient in list(campaign.recipients):
        if recipient.status in {"sent", "delivered"}:
            delivered += 1
            continue
        if not recipient.email:
            recipient.status = "skipped"
            recipient.error_message = "Destinatario sem email."
            skipped += 1
            continue
        try:
            send_result = _send_with_provider(campaign, recipient)
            provider_message_id = send_result.message_id
            recipient.provider_message_id = provider_message_id
            recipient.status = "delivered" if send_result.event_type == "delivered" else "sent"
            recipient.sent_at = now
            recipient.delivered_at = now if send_result.event_type == "delivered" else None
            _record_event(
                db,
                campaign=campaign,
                recipient=recipient,
                event_type=send_result.event_type,
                status="ok",
                provider_event_id=f"{campaign.provider}_event_{recipient.id}_sent",
                payload={"messageId": provider_message_id, "provider": send_result.provider, **send_result.metadata},
            )
            delivered += 1
        except Exception as exc:
            recipient.status = "failed"
            recipient.error_message = str(exc)[:2000]
            _record_event(
                db,
                campaign=campaign,
                recipient=recipient,
                event_type="failed",
                status="failed",
                provider_event_id=f"{campaign.provider}_event_{recipient.id}_failed",
                payload={"error": str(exc)},
            )
            failed += 1

    campaign.delivered_count = delivered
    campaign.failed_count = failed
    campaign.skipped_count = skipped
    campaign.status = "sent" if failed == 0 else "failed"
    campaign.completed_at = datetime.now(UTC)
    campaign.updated_at = campaign.completed_at
    _audit(
        db,
        user_id=actor_user_id,
        action="distribution_campaign_dispatched",
        message=f"Campanha enviada: {delivered} entregues, {failed} falhas, {skipped} ignorados.",
        resource_id=campaign.id,
        metadata={"delivered": delivered, "failed": failed, "skipped": skipped, "provider": campaign.provider},
    )
    if commit:
        db.commit()
        db.refresh(campaign)
    return campaign_to_dict(campaign, include_recipients=True)


def process_distribution_webhook(
    db: Session,
    *,
    provider: str,
    payload: dict[str, Any],
    signature_header: str = "",
    commit: bool = True,
) -> dict[str, Any]:
    normalized_provider = _normalize_provider(provider)
    if not _verify_signature(normalized_provider, payload, signature_header):
        raise DistributionEngineError("Assinatura do webhook de distribuicao invalida.")
    provider_event_id = str(payload.get("id") or payload.get("event_id") or _hash_payload(payload))[:160]
    existing = db.execute(
        select(DistributionEventLog).where(
            DistributionEventLog.provider == normalized_provider,
            DistributionEventLog.provider_event_id == provider_event_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return {"event": distribution_event_to_dict(existing), "duplicate": True}

    campaign = _find_campaign_for_webhook(db, normalized_provider, payload)
    recipient = _find_recipient_for_webhook(db, campaign, payload)
    event_type = str(payload.get("type") or payload.get("event_type") or "provider_event")[:80]
    event = _record_event(
        db,
        campaign=campaign,
        recipient=recipient,
        event_type=event_type,
        status="received",
        provider_event_id=provider_event_id,
        payload=payload,
    )
    _apply_recipient_event(recipient, event_type)
    _recount_campaign(campaign)
    if commit:
        db.commit()
        db.refresh(event)
    return {"event": distribution_event_to_dict(event), "duplicate": False}


def list_distribution_campaigns(db: Session, *, limit: int = 100) -> dict[str, Any]:
    safe_limit = min(max(limit, 1), 300)
    rows = list(
        db.execute(select(DistributionCampaign).order_by(desc(DistributionCampaign.created_at)).limit(safe_limit))
        .scalars()
        .all()
    )
    return {"items": [campaign_to_dict(row, include_recipients=False) for row in rows], "count": len(rows), "limit": safe_limit}


def campaign_to_dict(campaign: DistributionCampaign, *, include_recipients: bool = False, include_events: bool = False) -> dict[str, Any]:
    payload = {
        "id": campaign.id,
        "publicationId": campaign.publication_id,
        "artifactId": campaign.artifact_id or "",
        "createdByUserId": campaign.created_by_user_id or "",
        "name": campaign.name,
        "channel": campaign.channel,
        "audienceType": campaign.audience_type,
        "provider": campaign.provider,
        "providerCampaignId": campaign.provider_campaign_id,
        "status": campaign.status,
        "subject": campaign.subject,
        "previewText": campaign.preview_text,
        "recipientCount": campaign.recipient_count,
        "deliveredCount": campaign.delivered_count,
        "failedCount": campaign.failed_count,
        "skippedCount": campaign.skipped_count,
        "openCount": campaign.open_count,
        "clickCount": campaign.click_count,
        "scheduledAt": campaign.scheduled_at.isoformat() if campaign.scheduled_at else "",
        "dispatchedAt": campaign.dispatched_at.isoformat() if campaign.dispatched_at else "",
        "completedAt": campaign.completed_at.isoformat() if campaign.completed_at else "",
        "payload": _json_load(campaign.payload_json, {}),
        "metadata": _json_load(campaign.metadata_json, {}),
        "artifact": artifact_to_dict(campaign.artifact, include_content=False) if campaign.artifact else None,
        "createdAt": campaign.created_at.isoformat() if campaign.created_at else "",
    }
    if include_recipients:
        payload["recipients"] = [recipient_to_dict(row) for row in sorted(campaign.recipients, key=lambda item: item.email)]
    if include_events:
        payload["events"] = [distribution_event_to_dict(row) for row in sorted(campaign.events, key=lambda item: item.created_at or datetime.min, reverse=True)]
    return payload


def recipient_to_dict(row: DistributionRecipient) -> dict[str, Any]:
    return {
        "id": row.id,
        "campaignId": row.campaign_id,
        "userId": row.user_id or "",
        "email": row.email,
        "fullName": row.full_name,
        "status": row.status,
        "providerMessageId": row.provider_message_id,
        "entitlementStatus": row.entitlement_status,
        "errorMessage": row.error_message,
        "sentAt": row.sent_at.isoformat() if row.sent_at else "",
        "deliveredAt": row.delivered_at.isoformat() if row.delivered_at else "",
        "openedAt": row.opened_at.isoformat() if row.opened_at else "",
        "clickedAt": row.clicked_at.isoformat() if row.clicked_at else "",
        "metadata": _json_load(row.metadata_json, {}),
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def distribution_event_to_dict(row: DistributionEventLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "campaignId": row.campaign_id,
        "recipientId": row.recipient_id or "",
        "provider": row.provider,
        "providerEventId": row.provider_event_id,
        "providerMessageId": row.provider_message_id,
        "eventType": row.event_type,
        "status": row.status,
        "payload": _json_load(row.payload_json, {}),
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def _resolve_artifact(db: Session, *, publication: ResearchPublication, artifact_id: str | None) -> PublicationArtifact | None:
    if artifact_id:
        artifact = db.get(PublicationArtifact, artifact_id)
        if artifact is None:
            raise DistributionEngineError("Artefato nao encontrado.")
        if artifact.artifact_type == "pdf" and not artifact.binary_content:
            raise DistributionEngineError("PDF selecionado nao possui conteudo binario.")
        return artifact
    return (
        db.execute(
            select(PublicationArtifact)
            .where(
                PublicationArtifact.publication_id == publication.id,
                PublicationArtifact.artifact_type == "pdf",
                PublicationArtifact.content_type == "application/pdf",
            )
            .order_by(desc(PublicationArtifact.created_at))
        )
        .scalars()
        .first()
    )


def _resolve_recipients(db: Session, *, audience_type: str, manual_user_ids: list[str]) -> list[dict[str, str]]:
    if audience_type in {"manual_user", "test_user"}:
        if not manual_user_ids:
            raise DistributionEngineError("Audiencia manual exige pelo menos um usuario.")
        users = list(db.execute(select(User).where(User.id.in_(manual_user_ids))).scalars().all())
        return [
            {"userId": user.id, "email": user.email, "fullName": user.full_name, "entitlementStatus": "manual", "source": audience_type}
            for user in users
        ]
    now = datetime.now(UTC)
    rows = list(
        db.execute(
            select(User)
            .join(PremiumEntitlement, PremiumEntitlement.user_id == User.id)
            .where(
                PremiumEntitlement.status == "active",
                PremiumEntitlement.entitlement_key.in_(READ_ENTITLEMENTS | DOWNLOAD_ENTITLEMENTS),
                or_(PremiumEntitlement.starts_at.is_(None), PremiumEntitlement.starts_at <= now),
                or_(PremiumEntitlement.expires_at.is_(None), PremiumEntitlement.expires_at >= now),
            )
            .group_by(User.id)
            .order_by(User.email)
        )
        .scalars()
        .all()
    )
    return [
        {"userId": user.id, "email": user.email, "fullName": user.full_name, "entitlementStatus": "active_entitlement", "source": "premium_entitlement"}
        for user in rows
    ]


def _distribution_payload(publication: ResearchPublication, artifact: PublicationArtifact | None) -> dict[str, Any]:
    return {
        "publication": {
            "id": publication.id,
            "period": publication.period,
            "title": publication.title,
            "subtitle": publication.subtitle,
            "status": publication.status,
            "version": publication.version,
            "publishedAt": publication.published_at.isoformat() if publication.published_at else "",
        },
        "artifact": artifact_to_dict(artifact, include_content=False) if artifact else None,
        "disclaimer": "Conteudo informativo. Nao representa promessa de rentabilidade nem ordem de compra ou venda.",
    }


def _send_with_provider(campaign: DistributionCampaign, recipient: DistributionRecipient) -> DistributionSendResult:
    provider = get_distribution_provider(campaign.provider)
    return provider.send(campaign=campaign, recipient=recipient)


def _record_event(
    db: Session,
    *,
    campaign: DistributionCampaign,
    recipient: DistributionRecipient | None,
    event_type: str,
    status: str,
    provider_event_id: str,
    payload: dict[str, Any],
) -> DistributionEventLog:
    existing = db.execute(
        select(DistributionEventLog).where(
            DistributionEventLog.provider == campaign.provider,
            DistributionEventLog.provider_event_id == provider_event_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    event = DistributionEventLog(
        campaign_id=campaign.id,
        recipient_id=recipient.id if recipient else None,
        provider=campaign.provider,
        provider_event_id=provider_event_id,
        provider_message_id=recipient.provider_message_id if recipient else "",
        event_type=event_type[:80],
        status=status[:32],
        payload_json=_json(payload),
    )
    db.add(event)
    db.flush()
    return event


def _find_campaign_for_webhook(db: Session, provider: str, payload: dict[str, Any]) -> DistributionCampaign:
    campaign_id = str(payload.get("campaign_id") or "")[:32]
    if campaign_id:
        row = db.get(DistributionCampaign, campaign_id)
        if row:
            return row
    provider_campaign_id = str(payload.get("provider_campaign_id") or "")[:160]
    row = db.execute(
        select(DistributionCampaign).where(
            DistributionCampaign.provider == provider,
            DistributionCampaign.provider_campaign_id == provider_campaign_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise DistributionEngineError("Campanha relacionada ao webhook nao foi encontrada.")
    return row


def _find_recipient_for_webhook(db: Session, campaign: DistributionCampaign, payload: dict[str, Any]) -> DistributionRecipient | None:
    recipient_id = str(payload.get("recipient_id") or "")[:32]
    if recipient_id:
        row = db.get(DistributionRecipient, recipient_id)
        if row and row.campaign_id == campaign.id:
            return row
    message_id = str(payload.get("provider_message_id") or payload.get("message_id") or "")[:160]
    if message_id:
        return db.execute(
            select(DistributionRecipient).where(
                DistributionRecipient.campaign_id == campaign.id,
                DistributionRecipient.provider_message_id == message_id,
            )
        ).scalar_one_or_none()
    return None


def _apply_recipient_event(recipient: DistributionRecipient | None, event_type: str) -> None:
    if recipient is None:
        return
    now = datetime.now(UTC)
    normalized = event_type.strip().lower()
    if normalized in {"delivered", "email.delivered"}:
        recipient.status = "delivered"
        recipient.delivered_at = now
    elif normalized in {"opened", "open", "email.opened"}:
        recipient.opened_at = now
    elif normalized in {"clicked", "click", "email.clicked"}:
        recipient.clicked_at = now
    elif normalized in {"failed", "bounce", "bounced", "email.bounced"}:
        recipient.status = "failed"
        recipient.error_message = "Evento de falha recebido do provider."


def _recount_campaign(campaign: DistributionCampaign) -> None:
    campaign.delivered_count = sum(1 for row in campaign.recipients if row.status in {"sent", "delivered"})
    campaign.failed_count = sum(1 for row in campaign.recipients if row.status == "failed")
    campaign.skipped_count = sum(1 for row in campaign.recipients if row.status == "skipped")
    campaign.open_count = sum(1 for row in campaign.recipients if row.opened_at)
    campaign.click_count = sum(1 for row in campaign.recipients if row.clicked_at)
    campaign.updated_at = datetime.now(UTC)


def _normalize_channel(value: str) -> str:
    channel = (value or "email").strip().lower()
    if channel not in SUPPORTED_CHANNELS:
        raise DistributionEngineError("Canal de distribuicao invalido.")
    return channel


def _normalize_audience(value: str) -> str:
    audience = (value or "premium_subscribers").strip().lower()
    if audience not in SUPPORTED_AUDIENCES:
        raise DistributionEngineError("Audiencia de distribuicao invalida.")
    return audience


def _provider() -> str:
    return _normalize_provider(get_settings().distribution_provider)


def _normalize_provider(value: str) -> str:
    normalized = (value or "mock").strip().lower().replace("-", "_")
    return normalized or "mock"


def _verify_signature(provider: str, payload: dict[str, Any], signature_header: str) -> bool:
    if provider == "mock":
        secret = get_settings().distribution_webhook_secret
        if not secret:
            return True
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature_header or "", expected)
    return False


def _audit(
    db: Session,
    *,
    user_id: str,
    action: str,
    message: str,
    resource_id: str,
    metadata: dict[str, Any],
) -> None:
    write_audit_event(
        db,
        event_type="distribution_engine",
        category="distribution",
        action=action,
        user_id=user_id,
        severity="info",
        resource_type="distribution_campaign",
        resource_id=resource_id,
        message=message,
        metadata={"engineVersion": DISTRIBUTION_ENGINE_VERSION, **metadata},
    )


def _hash_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
