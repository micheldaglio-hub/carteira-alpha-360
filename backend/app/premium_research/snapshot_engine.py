from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from math import isfinite
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    PublicationApproval,
    PublicationAsset,
    PublicationEvidence,
    PublicationReview,
    PublicationSection,
    PublicationSnapshot,
    PublicationSource,
    PublicationVersion,
    ResearchAttributionRun,
    ResearchCommitteeRun,
    ResearchPublication,
)
from app.services.data_lineage import record_data_evidence


SNAPSHOT_ENGINE_VERSION = "2026.07.snapshot1"
DEFAULT_SNAPSHOT_TYPE = "approved_edition"


class PublicationSnapshotError(ValueError):
    """Raised when a premium publication cannot be snapshotted safely."""


def create_publication_snapshot(
    db: Session,
    *,
    publication: ResearchPublication,
    publication_version: PublicationVersion | None = None,
    user_id: str | None = None,
    snapshot_type: str = DEFAULT_SNAPSHOT_TYPE,
    require_approval: bool = True,
    commit: bool = True,
) -> dict[str, Any]:
    """Create an immutable editorial package for a premium publication version.

    The snapshot is append-only by design: one snapshot type per version. The
    service stores the canonical payload and a SHA-256 hash so a future PDF,
    web page, delivery log or correction can point to the exact edition that
    existed at approval time.
    """

    version = publication_version or _latest_version(db, publication)
    if version is None:
        raise PublicationSnapshotError("Publicacao premium sem versao para gerar snapshot.")

    snapshot_type = (snapshot_type or DEFAULT_SNAPSHOT_TYPE).strip()[:80] or DEFAULT_SNAPSHOT_TYPE
    existing = db.execute(
        select(PublicationSnapshot).where(
            PublicationSnapshot.publication_version_id == version.id,
            PublicationSnapshot.snapshot_type == snapshot_type,
        )
    ).scalar_one_or_none()
    if existing is not None:
        payload = snapshot_to_dict(existing)
        payload["alreadyExists"] = True
        return payload

    review = _latest_review(db, publication, version)
    approval = _latest_approval(db, publication, version)
    if require_approval:
        _assert_ready_for_snapshot(publication, version, review, approval)

    committee = _latest_committee(db, publication, version)
    attribution = _latest_attribution(db, publication, version)
    sections = _version_sections(db, publication, version)
    assets = _version_assets(db, publication, version)
    sources = _version_sources(db, publication, version)
    evidence = _version_evidence(db, publication, version)

    content_payload = {
        "publication": _publication_payload(publication),
        "version": _version_payload(version),
        "sections": [_section_payload(row) for row in sections],
        "assets": [_asset_payload(row) for row in assets],
    }
    source_payload = {
        "sources": [_source_payload(row) for row in sources],
        "evidence": [_evidence_payload(row) for row in evidence],
    }
    approval_payload = {
        "review": _review_payload(review),
        "approval": _approval_payload(approval),
        "committee": _committee_payload(committee),
    }
    attribution_payload = _attribution_payload(attribution)

    content_hash = _hash_payload(content_payload)
    source_hash = _hash_payload(source_payload)
    evidence_hash = _hash_payload(source_payload["evidence"])
    approval_hash = _hash_payload(approval_payload)
    manifest = {
        "engineVersion": SNAPSHOT_ENGINE_VERSION,
        "snapshotType": snapshot_type,
        "publicationId": publication.id,
        "publicationVersionId": version.id,
        "period": publication.period,
        "version": version.version,
        "versionHash": version.version_hash,
        "contentHash": content_hash,
        "sourceHash": source_hash,
        "evidenceHash": evidence_hash,
        "approvalHash": approval_hash,
        "sectionCount": len(sections),
        "assetCount": len(assets),
        "sourceCount": len(sources),
        "evidenceCount": len(evidence),
        "committeeRunId": committee.id if committee else "",
        "attributionRunId": attribution.id if attribution else "",
        "reviewId": review.id if review else "",
        "approvalId": approval.id if approval else "",
        "createdAt": datetime.now(UTC).isoformat(),
    }
    canonical_payload = {
        **content_payload,
        **source_payload,
        "committee": approval_payload["committee"],
        "review": approval_payload["review"],
        "approval": approval_payload["approval"],
        "attribution": attribution_payload,
        "legalDisclaimer": publication.legal_disclaimer,
        "snapshotManifest": manifest,
    }
    snapshot_hash = _hash_payload(canonical_payload)

    snapshot = PublicationSnapshot(
        publication_id=publication.id,
        publication_version_id=version.id,
        period=publication.period,
        snapshot_type=snapshot_type,
        status="locked",
        version_label=version.version,
        publication_status=publication.status,
        version_status=version.status,
        snapshot_hash=snapshot_hash,
        content_hash=content_hash,
        source_hash=source_hash,
        evidence_hash=evidence_hash,
        approval_hash=approval_hash,
        committee_run_id=committee.id if committee else None,
        attribution_run_id=attribution.id if attribution else None,
        review_id=review.id if review else None,
        approval_id=approval.id if approval else None,
        section_count=len(sections),
        asset_count=len(assets),
        source_count=len(sources),
        evidence_count=len(evidence),
        is_immutable=True,
        payload_json=_json(canonical_payload),
        manifest_json=_json(manifest),
        evidence_ids_json="[]",
        metadata_json=_json(
            {
                "requireApproval": require_approval,
                "publicationTitle": publication.title,
                "snapshotPurpose": "immutable_premium_edition_package",
            }
        ),
        created_by_user_id=user_id,
    )
    db.add(snapshot)
    db.flush()

    evidence_row = record_data_evidence(
        db,
        user_id=user_id,
        domain="premium_research_snapshot",
        field_name="snapshot_hash",
        value_text=snapshot_hash,
        unit="sha256",
        provider="publication_snapshot_engine",
        source_type="formula",
        source_ref=f"researchPublication:{publication.id}:version:{version.id}:snapshot:{snapshot.id}",
        formula_name="publication_snapshot_canonical_hash",
        formula_version=SNAPSHOT_ENGINE_VERSION,
        input_payload={
            "publicationId": publication.id,
            "versionId": version.id,
            "snapshotType": snapshot_type,
            "contentHash": content_hash,
            "sourceHash": source_hash,
            "evidenceHash": evidence_hash,
            "approvalHash": approval_hash,
        },
        confidence=96,
        quality_score=96,
        status="ok",
        metadata={"snapshotId": snapshot.id, "snapshotHash": snapshot_hash},
    )
    snapshot.evidence_ids_json = _json([evidence_row.id])

    if commit:
        db.commit()
        db.refresh(snapshot)
    return snapshot_to_dict(snapshot)


def snapshot_to_dict(snapshot: PublicationSnapshot, *, include_payload: bool = False) -> dict[str, Any]:
    integrity = verify_snapshot_integrity(snapshot)
    payload = {
        "id": snapshot.id,
        "publicationId": snapshot.publication_id,
        "publicationVersionId": snapshot.publication_version_id,
        "period": snapshot.period,
        "snapshotType": snapshot.snapshot_type,
        "status": snapshot.status,
        "versionLabel": snapshot.version_label,
        "publicationStatus": snapshot.publication_status,
        "versionStatus": snapshot.version_status,
        "snapshotHash": snapshot.snapshot_hash,
        "contentHash": snapshot.content_hash,
        "sourceHash": snapshot.source_hash,
        "evidenceHash": snapshot.evidence_hash,
        "approvalHash": snapshot.approval_hash,
        "committeeRunId": snapshot.committee_run_id,
        "attributionRunId": snapshot.attribution_run_id,
        "reviewId": snapshot.review_id,
        "approvalId": snapshot.approval_id,
        "sectionCount": snapshot.section_count,
        "assetCount": snapshot.asset_count,
        "sourceCount": snapshot.source_count,
        "evidenceCount": snapshot.evidence_count,
        "isImmutable": snapshot.is_immutable,
        "integrity": integrity,
        "manifest": _json_load(snapshot.manifest_json, {}),
        "evidenceIds": _json_load(snapshot.evidence_ids_json, []),
        "metadata": _json_load(snapshot.metadata_json, {}),
        "createdByUserId": snapshot.created_by_user_id,
        "lockedAt": snapshot.locked_at.isoformat() if snapshot.locked_at else "",
        "createdAt": snapshot.created_at.isoformat() if snapshot.created_at else "",
    }
    if include_payload:
        payload["payload"] = _json_load(snapshot.payload_json, {})
    return payload


def verify_snapshot_integrity(snapshot: PublicationSnapshot) -> dict[str, Any]:
    payload = _json_load(snapshot.payload_json, {})
    recomputed = _hash_payload(payload)
    manifest = _json_load(snapshot.manifest_json, {})
    return {
        "status": "ok" if recomputed == snapshot.snapshot_hash else "tampered",
        "storedHash": snapshot.snapshot_hash,
        "recomputedHash": recomputed,
        "contentHashMatches": manifest.get("contentHash") == snapshot.content_hash,
        "sourceHashMatches": manifest.get("sourceHash") == snapshot.source_hash,
        "evidenceHashMatches": manifest.get("evidenceHash") == snapshot.evidence_hash,
        "approvalHashMatches": manifest.get("approvalHash") == snapshot.approval_hash,
    }


def _assert_ready_for_snapshot(
    publication: ResearchPublication,
    version: PublicationVersion,
    review: PublicationReview | None,
    approval: PublicationApproval | None,
) -> None:
    if publication.status != "approved" or version.status != "approved":
        raise PublicationSnapshotError("Snapshot final exige publicacao e versao com status approved.")
    if review is None or review.decision != "approve":
        raise PublicationSnapshotError("Snapshot final exige revisao humana aprovada.")
    if approval is None or approval.decision != "approve_publication":
        raise PublicationSnapshotError("Snapshot final exige aprovacao humana final.")


def _latest_version(db: Session, publication: ResearchPublication) -> PublicationVersion | None:
    return db.execute(
        select(PublicationVersion)
        .where(PublicationVersion.publication_id == publication.id)
        .order_by(desc(PublicationVersion.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _latest_review(db: Session, publication: ResearchPublication, version: PublicationVersion) -> PublicationReview | None:
    return db.execute(
        select(PublicationReview)
        .where(
            PublicationReview.publication_id == publication.id,
            PublicationReview.version_id == version.id,
            PublicationReview.decision == "approve",
        )
        .order_by(desc(PublicationReview.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _latest_approval(db: Session, publication: ResearchPublication, version: PublicationVersion) -> PublicationApproval | None:
    return db.execute(
        select(PublicationApproval)
        .where(
            PublicationApproval.publication_id == publication.id,
            PublicationApproval.version_id == version.id,
            PublicationApproval.decision == "approve_publication",
        )
        .order_by(desc(PublicationApproval.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _latest_committee(db: Session, publication: ResearchPublication, version: PublicationVersion) -> ResearchCommitteeRun | None:
    return db.execute(
        select(ResearchCommitteeRun)
        .where(
            ResearchCommitteeRun.publication_id == publication.id,
            ResearchCommitteeRun.publication_version_id == version.id,
        )
        .order_by(desc(ResearchCommitteeRun.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _latest_attribution(db: Session, publication: ResearchPublication, version: PublicationVersion) -> ResearchAttributionRun | None:
    return db.execute(
        select(ResearchAttributionRun)
        .where(
            ResearchAttributionRun.publication_id == publication.id,
            ResearchAttributionRun.publication_version_id == version.id,
        )
        .order_by(desc(ResearchAttributionRun.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _version_sections(db: Session, publication: ResearchPublication, version: PublicationVersion) -> list[PublicationSection]:
    return list(
        db.execute(
            select(PublicationSection)
            .where(PublicationSection.publication_id == publication.id, PublicationSection.version_id == version.id)
            .order_by(PublicationSection.section_order.asc(), PublicationSection.section_key.asc())
        )
        .scalars()
        .all()
    )


def _version_assets(db: Session, publication: ResearchPublication, version: PublicationVersion) -> list[PublicationAsset]:
    return list(
        db.execute(
            select(PublicationAsset)
            .where(PublicationAsset.publication_id == publication.id, PublicationAsset.version_id == version.id)
            .order_by(PublicationAsset.target_weight.desc(), PublicationAsset.ticker.asc())
        )
        .scalars()
        .all()
    )


def _version_sources(db: Session, publication: ResearchPublication, version: PublicationVersion) -> list[PublicationSource]:
    return list(
        db.execute(
            select(PublicationSource)
            .where(PublicationSource.publication_id == publication.id, PublicationSource.version_id == version.id)
            .order_by(PublicationSource.provider.asc(), PublicationSource.source_ref.asc())
        )
        .scalars()
        .all()
    )


def _version_evidence(db: Session, publication: ResearchPublication, version: PublicationVersion) -> list[PublicationEvidence]:
    return list(
        db.execute(
            select(PublicationEvidence)
            .where(PublicationEvidence.publication_id == publication.id, PublicationEvidence.version_id == version.id)
            .order_by(PublicationEvidence.domain.asc(), PublicationEvidence.field_name.asc(), PublicationEvidence.id.asc())
        )
        .scalars()
        .all()
    )


def _publication_payload(row: ResearchPublication) -> dict[str, Any]:
    return {
        "id": row.id,
        "publicationType": row.publication_type,
        "period": row.period,
        "title": row.title,
        "subtitle": row.subtitle,
        "referenceDate": row.reference_date.isoformat() if row.reference_date else "",
        "closingDate": row.closing_date.isoformat() if row.closing_date else "",
        "status": row.status,
        "version": row.version,
        "confidence": _round(_number(row.confidence), 2),
        "partialDataCount": row.partial_data_count,
        "fallbackCount": row.fallback_count,
        "versionHash": row.version_hash,
    }


def _version_payload(row: PublicationVersion) -> dict[str, Any]:
    return {
        "id": row.id,
        "version": row.version,
        "status": row.status,
        "versionHash": row.version_hash,
        "readinessScore": _round(_number(row.readiness_score), 2),
        "readinessClassification": row.readiness_classification,
        "sourceCount": row.source_count,
        "partialDataCount": row.partial_data_count,
        "fallbackCount": row.fallback_count,
        "payload": _json_load(row.payload_json, {}),
        "changelog": _json_load(row.changelog_json, []),
    }


def _section_payload(row: PublicationSection) -> dict[str, Any]:
    return {
        "id": row.id,
        "key": row.section_key,
        "title": row.title,
        "order": row.section_order,
        "status": row.status,
        "confidence": _round(_number(row.confidence), 2),
        "contentMarkdown": row.content_markdown,
        "content": _json_load(row.content_json, {}),
        "dataGaps": _json_load(row.data_gaps_json, []),
        "evidenceIds": _json_load(row.evidence_ids_json, []),
        "requiresHumanApproval": row.requires_human_approval,
    }


def _asset_payload(row: PublicationAsset) -> dict[str, Any]:
    return {
        "id": row.id,
        "assetId": row.asset_id,
        "ticker": row.ticker,
        "assetName": row.asset_name,
        "role": row.role,
        "action": row.action,
        "targetWeight": _round(_number(row.target_weight), 4),
        "previousWeight": _round(_number(row.previous_weight), 4),
        "rating": row.rating,
        "thesisStatus": row.thesis_status,
        "evidenceIds": _json_load(row.evidence_ids_json, []),
        "metadata": _json_load(row.metadata_json, {}),
    }


def _source_payload(row: PublicationSource) -> dict[str, Any]:
    return {
        "id": row.id,
        "sourceType": row.source_type,
        "provider": row.provider,
        "sourceRef": row.source_ref,
        "title": row.title,
        "url": row.url,
        "confidence": _round(_number(row.confidence), 2),
        "status": row.status,
        "observedAt": row.observed_at.isoformat() if row.observed_at else "",
        "metadata": _json_load(row.metadata_json, {}),
    }


def _evidence_payload(row: PublicationEvidence) -> dict[str, Any]:
    return {
        "id": row.id,
        "sectionId": row.section_id,
        "evidenceId": row.evidence_id,
        "evidenceKey": row.evidence_key,
        "domain": row.domain,
        "fieldName": row.field_name,
        "provider": row.provider,
        "sourceType": row.source_type,
        "confidence": _round(_number(row.confidence), 2),
        "status": row.status,
        "metadata": _json_load(row.metadata_json, {}),
    }


def _committee_payload(row: ResearchCommitteeRun | None) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": row.id,
        "decision": row.decision,
        "status": row.status,
        "readinessScore": _round(_number(row.readiness_score), 2),
        "approvalScore": _round(_number(row.approval_score), 2),
        "blockerCount": row.blocker_count,
        "warningCount": row.warning_count,
        "gateCount": row.gate_count,
        "voteCount": row.vote_count,
        "summary": row.summary,
        "blockers": _json_load(row.blockers_json, []),
        "warnings": _json_load(row.warnings_json, []),
        "methodologyVersion": row.methodology_version,
    }


def _attribution_payload(row: ResearchAttributionRun | None) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": row.id,
        "period": row.period,
        "startDate": row.start_date.isoformat() if row.start_date else "",
        "endDate": row.end_date.isoformat() if row.end_date else "",
        "portfolioReturnPct": _round(_number(row.portfolio_return_pct), 4),
        "benchmarkName": row.benchmark_name,
        "benchmarkReturnPct": _round(_number(row.benchmark_return_pct), 4),
        "excessReturnPct": _round(_number(row.excess_return_pct), 4),
        "priceReturnPct": _round(_number(row.price_return_pct), 4),
        "incomeReturnPct": _round(_number(row.income_return_pct), 4),
        "dataQualityScore": _round(_number(row.data_quality_score), 2),
        "summary": row.summary,
        "topContributors": _json_load(row.top_contributors_json, []),
        "detractors": _json_load(row.detractors_json, []),
        "warnings": _json_load(row.warnings_json, []),
        "methodologyVersion": row.methodology_version,
    }


def _review_payload(row: PublicationReview | None) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": row.id,
        "reviewerUserId": row.reviewer_user_id,
        "decision": row.decision,
        "status": row.status,
        "comments": row.comments,
        "requestedChanges": _json_load(row.requested_changes_json, []),
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def _approval_payload(row: PublicationApproval | None) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": row.id,
        "approverUserId": row.approver_user_id,
        "decision": row.decision,
        "comments": row.comments,
        "approvedAt": row.approved_at.isoformat() if row.approved_at else "",
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def _hash_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_load(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw or "")
    except Exception:
        return fallback


def _number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        number = float(value)
        return number if isfinite(number) else 0.0
    except Exception:
        return 0.0


def _round(value: float, digits: int = 2) -> float:
    return round(_number(value), digits)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(_round(_number(value), 6)))
