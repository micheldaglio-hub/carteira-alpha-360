from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models import DistributionRecipient, PremiumAccessLog, PublicationArtifact, User
from app.premium_research.entitlements import DOWNLOAD_ACTION, inspect_premium_artifact_access
from app.premium_research.renderer import artifact_to_dict


DELIVERY_INBOX_VERSION = "2026.07.delivery_inbox1"


def list_subscriber_delivery_inbox(
    db: Session,
    *,
    user: User,
    limit: int = 80,
) -> dict[str, Any]:
    safe_limit = min(max(limit, 1), 200)
    rows = list(
        db.execute(
            select(DistributionRecipient)
            .where(
                or_(
                    DistributionRecipient.user_id == user.id,
                    DistributionRecipient.email == user.email,
                )
            )
            .order_by(desc(DistributionRecipient.created_at))
            .limit(safe_limit)
        )
        .scalars()
        .all()
    )
    download_logs = _download_logs_for_recipients(db, user_id=user.id, recipients=rows)
    items = [delivery_inbox_item_to_dict(db, user=user, recipient=row, download_logs=download_logs) for row in rows]
    return {
        "items": items,
        "summary": _summary(items),
        "count": len(items),
        "limit": safe_limit,
        "engineVersion": DELIVERY_INBOX_VERSION,
    }


def delivery_inbox_item_to_dict(
    db: Session,
    *,
    user: User,
    recipient: DistributionRecipient,
    download_logs: list[PremiumAccessLog],
) -> dict[str, Any]:
    campaign = recipient.campaign
    publication = campaign.publication if campaign else None
    artifact = campaign.artifact if campaign else None
    related_downloads = [
        row
        for row in download_logs
        if (artifact and row.artifact_id == artifact.id) or (publication and row.publication_id == publication.id)
    ]
    latest_download = max(related_downloads, key=lambda row: row.created_at or datetime.min, default=None)
    downloaded = latest_download is not None
    delivery_status = _delivery_status(recipient, downloaded=downloaded)
    can_download, access_reason = _artifact_access(db, user=user, artifact=artifact)
    return {
        "id": recipient.id,
        "campaignId": recipient.campaign_id,
        "recipientStatus": recipient.status,
        "deliveryStatus": delivery_status,
        "deliveryStatusLabel": _status_label(delivery_status),
        "subject": campaign.subject if campaign else "",
        "previewText": campaign.preview_text if campaign else "",
        "provider": campaign.provider if campaign else "",
        "channel": campaign.channel if campaign else "",
        "publication": _publication_payload(publication),
        "artifact": artifact_to_dict(artifact, include_content=False) if artifact else None,
        "downloadUrl": f"/api/premium/artifacts/{artifact.id}/download" if artifact else "",
        "canDownload": can_download,
        "accessReason": access_reason,
        "downloaded": downloaded,
        "downloadCount": len(related_downloads),
        "lastDownloadAt": latest_download.created_at.isoformat() if latest_download and latest_download.created_at else "",
        "sentAt": recipient.sent_at.isoformat() if recipient.sent_at else "",
        "deliveredAt": recipient.delivered_at.isoformat() if recipient.delivered_at else "",
        "openedAt": recipient.opened_at.isoformat() if recipient.opened_at else "",
        "clickedAt": recipient.clicked_at.isoformat() if recipient.clicked_at else "",
        "createdAt": recipient.created_at.isoformat() if recipient.created_at else "",
        "errorMessage": recipient.error_message,
        "metadata": _json_load(recipient.metadata_json, {}),
    }


def _download_logs_for_recipients(
    db: Session,
    *,
    user_id: str,
    recipients: list[DistributionRecipient],
) -> list[PremiumAccessLog]:
    publication_ids = {row.campaign.publication_id for row in recipients if row.campaign and row.campaign.publication_id}
    artifact_ids = {row.campaign.artifact_id for row in recipients if row.campaign and row.campaign.artifact_id}
    if not publication_ids and not artifact_ids:
        return []
    clauses = []
    if publication_ids:
        clauses.append(PremiumAccessLog.publication_id.in_(publication_ids))
    if artifact_ids:
        clauses.append(PremiumAccessLog.artifact_id.in_(artifact_ids))
    return list(
        db.execute(
            select(PremiumAccessLog)
            .where(
                PremiumAccessLog.user_id == user_id,
                PremiumAccessLog.action == DOWNLOAD_ACTION,
                PremiumAccessLog.allowed.is_(True),
                or_(*clauses),
            )
            .order_by(desc(PremiumAccessLog.created_at))
        )
        .scalars()
        .all()
    )


def _artifact_access(db: Session, *, user: User, artifact: PublicationArtifact | None) -> tuple[bool, str]:
    if artifact is None:
        return False, "missing_artifact"
    inspection = inspect_premium_artifact_access(
        db,
        user_id=user.id,
        artifact=artifact,
        action=DOWNLOAD_ACTION,
        editorial_owner=False,
    )
    return bool(inspection.get("allowed")), str(inspection.get("reason") or "")


def _delivery_status(recipient: DistributionRecipient, *, downloaded: bool) -> str:
    if downloaded:
        return "downloaded"
    if recipient.status == "failed":
        return "failed"
    if recipient.status == "skipped":
        return "skipped"
    if recipient.clicked_at:
        return "clicked"
    if recipient.opened_at:
        return "opened"
    if recipient.delivered_at or recipient.status == "delivered":
        return "received"
    if recipient.sent_at or recipient.status == "sent":
        return "sent"
    return "pending"


def _status_label(status: str) -> str:
    labels = {
        "pending": "Pendente",
        "sent": "Enviada",
        "received": "Recebida",
        "opened": "Aberta",
        "clicked": "Clicada",
        "downloaded": "Baixada",
        "failed": "Falhou",
        "skipped": "Ignorada",
    }
    return labels.get(status, status)


def _summary(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total": len(items),
        "pending": 0,
        "sent": 0,
        "received": 0,
        "opened": 0,
        "clicked": 0,
        "downloaded": 0,
        "failed": 0,
        "skipped": 0,
    }
    for item in items:
        status = item.get("deliveryStatus") or "pending"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _publication_payload(publication: Any) -> dict[str, Any]:
    if publication is None:
        return {}
    return {
        "id": publication.id,
        "period": publication.period,
        "title": publication.title,
        "subtitle": publication.subtitle,
        "status": publication.status,
        "version": publication.version,
        "confidence": _number(publication.confidence),
        "publishedAt": publication.published_at.isoformat() if publication.published_at else "",
        "createdAt": publication.created_at.isoformat() if publication.created_at else "",
    }


def _json_load(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
