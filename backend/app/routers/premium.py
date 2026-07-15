from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, false, or_, select, true
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.distribution.inbox import list_subscriber_delivery_inbox
from app.models import (
    AssetRating,
    AssetRatingVersion,
    AssetThesis,
    AssetThesisVersion,
    PublicationArtifact,
    PublicationApproval,
    PublicationReview,
    PublicationSnapshot,
    PublicationVersion,
    ResearchAttributionRun,
    ResearchCommitteeRun,
    ResearchPublication,
    SubscriptionPlan,
    User,
)
from app.premium_research.entitlements import (
    DOWNLOAD_ACTION,
    authorize_premium_artifact_access,
    grant_subscription_to_user,
    inspect_premium_artifact_access,
    list_premium_access_logs,
    list_user_premium_access,
    plan_to_dict,
    seed_default_subscription_plans,
)
from app.premium_research.performance_attribution import (
    attribution_run_to_dict,
    run_performance_attribution_for_publication,
)
from app.premium_research.pdf_publisher import PublicationPdfError, render_pdf_from_html_artifact
from app.premium_research.publisher import create_premium_research_draft, publication_to_dict
from app.premium_research.rating_engine import rating_version_to_dict, sync_ratings_for_publication
from app.premium_research.research_committee import committee_run_to_dict, run_research_committee_for_publication
from app.premium_research.renderer import (
    PublicationRenderError,
    artifact_to_dict,
    render_publication_snapshot,
)
from app.premium_research.snapshot_engine import (
    PublicationSnapshotError,
    create_publication_snapshot,
    snapshot_to_dict,
)
from app.premium_research.thesis_engine import sync_theses_from_recommended_report, thesis_version_to_dict
from app.services.audit import write_audit_event
from app.services.model_portfolios import get_model_portfolios
from app.services.rbac import (
    ADMIN_ROLES,
    APPROVAL_ROLES,
    EDITORIAL_ROLES,
    PUBLISHER_ROLES,
    REVIEW_ROLES,
    grant_role_to_user,
    rbac_summary,
    require_any_role,
    role_to_dict,
    user_has_any_role,
    valid_roles,
)


router = APIRouter(prefix="/premium", tags=["premium-research"])


class PremiumDraftRequest(BaseModel):
    period: str | None = Field(default=None, max_length=40)
    publication_type: str = Field(default="monthly_research", max_length=80)
    title: str | None = Field(default=None, max_length=220)
    refresh_market: bool = False


class PremiumSyncRequest(BaseModel):
    publication_version_id: str | None = Field(default=None, max_length=32)
    force_new_version: bool = False
    refresh_market: bool = False
    run_committee: bool = True


class CommitteeRunRequest(BaseModel):
    publication_version_id: str | None = Field(default=None, max_length=32)


class AttributionRunRequest(BaseModel):
    publication_version_id: str | None = Field(default=None, max_length=32)
    start_date: date | None = None
    end_date: date | None = None
    benchmark_name: str = Field(default="", max_length=120)
    benchmark_return_pct: float | None = None
    refresh_market: bool = False


class PublicationReviewRequest(BaseModel):
    publication_version_id: str | None = Field(default=None, max_length=32)
    decision: Literal["approve", "request_changes", "block"] = "request_changes"
    comments: str = Field(default="", max_length=5000)
    requested_changes: list[str] = Field(default_factory=list)


class PublicationApprovalRequest(BaseModel):
    publication_version_id: str | None = Field(default=None, max_length=32)
    decision: Literal["approve_publication", "reject_publication"] = "reject_publication"
    comments: str = Field(default="", max_length=5000)


class PublicationSnapshotRequest(BaseModel):
    publication_version_id: str | None = Field(default=None, max_length=32)
    snapshot_type: str = Field(default="approved_edition", max_length=80)
    require_approval: bool = True
    include_payload: bool = False


class PublicationRenderRequest(BaseModel):
    artifact_type: str = Field(default="html", max_length=80)
    force: bool = False
    include_content: bool = False


class PublicationPdfRequest(BaseModel):
    force: bool = False


class SubscriptionGrantRequest(BaseModel):
    user_id: str | None = Field(default=None, max_length=32)
    plan_code: str = Field(default="alpha_premium", max_length=80)
    period_days: int = Field(default=30, ge=1, le=3660)


class RoleGrantRequest(BaseModel):
    user_id: str = Field(max_length=32)
    role: str = Field(max_length=80)
    scope_type: str = Field(default="global", max_length=40)
    scope_id: str = Field(default="*", max_length=120)


@router.post("/publications/drafts", status_code=status.HTTP_201_CREATED)
def create_publication_draft(
    payload: PremiumDraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_publisher(db, user)
    result = create_premium_research_draft(
        db,
        user_id=user.id,
        period=payload.period,
        publication_type=payload.publication_type,
        title=payload.title,
        refresh_market=payload.refresh_market,
        created_by_user_id=user.id,
    )
    write_audit_event(
        db,
        event_type="premium_research_draft_created",
        category="premium_research",
        action="create_draft",
        user_id=user.id,
        severity="info",
        resource_type="research_publication",
        resource_id=result["id"],
        message="Rascunho premium criado por endpoint administrativo protegido.",
        metadata={"period": result.get("period"), "version": result.get("version"), "status": result.get("status")},
    )
    return result


@router.post("/plans/seed", status_code=status.HTTP_201_CREATED)
def seed_plans(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(db, user)
    plans = seed_default_subscription_plans(db, commit=True)
    write_audit_event(
        db,
        event_type="premium_subscription_plans_seeded",
        category="premium_entitlements",
        action="seed_plans",
        user_id=user.id,
        severity="info",
        resource_type="subscription_plan",
        resource_id="default_plans",
        message="Planos premium padrao sincronizados.",
        metadata={"count": len(plans)},
    )
    return {"items": [plan_to_dict(plan) for plan in plans], "count": len(plans)}


@router.get("/plans")
def list_plans(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    seed_default_subscription_plans(db, commit=True)
    plans = list(db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.monthly_price)).scalars().all())
    return {"items": [plan_to_dict(plan) for plan in plans], "count": len(plans)}


@router.post("/subscriptions/grant", status_code=status.HTTP_201_CREATED)
def grant_subscription(
    payload: SubscriptionGrantRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(db, user)
    target_user_id = payload.user_id or user.id
    if db.get(User, target_user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario alvo nao encontrado.")
    try:
        result = grant_subscription_to_user(
            db,
            user_id=target_user_id,
            plan_code=payload.plan_code,
            period_days=payload.period_days,
            metadata={"grantedBy": "premium_admin_api", "actorUserId": user.id},
            commit=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    write_audit_event(
        db,
        event_type="premium_subscription_granted",
        category="premium_entitlements",
        action="grant_subscription",
        user_id=user.id,
        severity="info",
        resource_type="user_subscription",
        resource_id=result["subscription"]["id"],
        message="Assinatura premium concedida por rota administrativa protegida.",
        metadata={"planCode": payload.plan_code, "periodDays": payload.period_days, "targetUserId": target_user_id},
    )
    return result


@router.get("/subscriptions/me")
def get_my_subscription_access(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_user_premium_access(db, user_id=user.id)


@router.get("/access-logs")
def get_my_access_logs(
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_premium_access_logs(db, user_id=user.id, limit=limit)


@router.get("/rbac/me")
def get_my_rbac(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return rbac_summary(db, user_id=user.id)


@router.post("/rbac/roles/grant", status_code=status.HTTP_201_CREATED)
def grant_rbac_role(
    payload: RoleGrantRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(db, user)
    if payload.role not in valid_roles():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Papel RBAC invalido.")
    if db.get(User, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario alvo nao encontrado.")
    row = grant_role_to_user(
        db,
        user_id=payload.user_id,
        role=payload.role,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        granted_by_user_id=user.id,
        source="premium_rbac_api",
        metadata={"actorUserId": user.id},
        commit=True,
    )
    write_audit_event(
        db,
        event_type="premium_rbac_role_granted",
        category="premium_rbac",
        action="grant_role",
        user_id=user.id,
        severity="info",
        resource_type="user_role",
        resource_id=row.id,
        message="Papel RBAC premium concedido por endpoint administrativo.",
        metadata={"targetUserId": payload.user_id, "role": payload.role, "scopeType": payload.scope_type, "scopeId": payload.scope_id},
    )
    return {"role": role_to_dict(row), "rbac": rbac_summary(db, user_id=payload.user_id)}


@router.get("/subscriber/home")
def subscriber_home(
    limit: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _subscriber_home(db, user, limit=limit)


@router.get("/subscriber/delivery-inbox")
def subscriber_delivery_inbox(
    limit: int = Query(default=80, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_subscriber_delivery_inbox(db, user=user, limit=limit)


@router.get("/publications")
def list_publications(
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    period: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    stmt = (
        select(ResearchPublication)
        .where(_publication_visible_to_user(db, user))
        .order_by(desc(ResearchPublication.created_at))
        .limit(limit)
    )
    if status_filter:
        stmt = stmt.where(ResearchPublication.status == status_filter)
    if period:
        stmt = stmt.where(ResearchPublication.period == period)
    publications = list(db.execute(stmt).scalars().all())
    return {
        "items": [publication_to_dict(item) for item in publications],
        "count": len(publications),
        "limit": limit,
    }


@router.get("/publications/{publication_id}")
def get_publication(
    publication_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    return _publication_detail(publication)


@router.get("/publications/{publication_id}/versions/{version_id}")
def get_publication_version(
    publication_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    version = _publication_version(db, publication, version_id)
    return _version_detail(version)


@router.post("/publications/{publication_id}/snapshots", status_code=status.HTTP_201_CREATED)
def create_snapshot(
    publication_id: str,
    payload: PublicationSnapshotRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_publisher(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    version = _selected_version(db, publication, payload.publication_version_id)
    try:
        snapshot = create_publication_snapshot(
            db,
            publication=publication,
            publication_version=version,
            user_id=user.id,
            snapshot_type=payload.snapshot_type,
            require_approval=payload.require_approval,
            commit=True,
        )
    except PublicationSnapshotError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    row = _owned_snapshot(db, snapshot["id"], user.id)
    result = snapshot_to_dict(row, include_payload=payload.include_payload)
    result["alreadyExists"] = snapshot.get("alreadyExists", False)
    write_audit_event(
        db,
        event_type="premium_research_snapshot_created",
        category="premium_research",
        action="create_snapshot",
        user_id=user.id,
        severity="info",
        resource_type="publication_snapshot",
        resource_id=result["id"],
        message="Snapshot imutavel da publicacao premium gerado por endpoint protegido.",
        metadata={
            "publicationId": publication.id,
            "versionId": version.id,
            "snapshotHash": result["snapshotHash"],
            "snapshotType": result["snapshotType"],
            "alreadyExists": result["alreadyExists"],
        },
    )
    return result


@router.get("/publications/{publication_id}/snapshots")
def list_publication_snapshots(
    publication_id: str,
    include_payload: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    rows = list(
        db.execute(
            select(PublicationSnapshot)
            .where(PublicationSnapshot.publication_id == publication.id)
            .order_by(desc(PublicationSnapshot.created_at))
        )
        .scalars()
        .all()
    )
    return {
        "items": [snapshot_to_dict(row, include_payload=include_payload) for row in rows],
        "count": len(rows),
    }


@router.get("/publications/{publication_id}/artifacts")
def list_publication_artifacts(
    publication_id: str,
    include_content: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    rows = list(
        db.execute(
            select(PublicationArtifact)
            .where(PublicationArtifact.publication_id == publication.id)
            .order_by(desc(PublicationArtifact.created_at))
        )
        .scalars()
        .all()
    )
    return {
        "items": [artifact_to_dict(row, include_content=include_content) for row in rows],
        "count": len(rows),
    }


@router.post("/publications/{publication_id}/theses/sync")
def sync_publication_theses(
    publication_id: str,
    payload: PremiumSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_publisher(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    version = _selected_version(db, publication, payload.publication_version_id)
    report = get_model_portfolios(db, user_id=user.id, refresh_market=payload.refresh_market)["recommendedPortfolioReport"]
    result = sync_theses_from_recommended_report(
        db,
        report,
        publication=publication,
        publication_version=version,
        user_id=user.id,
        force_new_version=payload.force_new_version,
        commit=True,
    )
    write_audit_event(
        db,
        event_type="premium_research_theses_synced",
        category="premium_research",
        action="sync_theses",
        user_id=user.id,
        severity="info",
        resource_type="publication_version",
        resource_id=version.id,
        message="Teses premium sincronizadas por endpoint administrativo protegido.",
        metadata={"publicationId": publication.id, "createdVersions": result.get("createdVersions")},
    )
    return {"publicationId": publication.id, "versionId": version.id, "thesisSync": result}


@router.post("/publications/{publication_id}/ratings/sync")
def sync_publication_ratings(
    publication_id: str,
    payload: PremiumSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_publisher(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    version = _selected_version(db, publication, payload.publication_version_id)
    rating_sync = sync_ratings_for_publication(
        db,
        publication=publication,
        publication_version=version,
        user_id=user.id,
        force_new_version=payload.force_new_version,
        commit=True,
    )
    committee = None
    if payload.run_committee:
        committee = run_research_committee_for_publication(
            db,
            publication=publication,
            publication_version=version,
            user_id=user.id,
            commit=True,
        )
    write_audit_event(
        db,
        event_type="premium_research_ratings_synced",
        category="premium_research",
        action="sync_ratings",
        user_id=user.id,
        severity="info",
        resource_type="publication_version",
        resource_id=version.id,
        message="Ratings premium sincronizados por endpoint administrativo protegido.",
        metadata={
            "publicationId": publication.id,
            "createdVersions": rating_sync.get("createdVersions"),
            "committeeDecision": (committee or {}).get("decision"),
        },
    )
    return {"publicationId": publication.id, "versionId": version.id, "ratingSync": rating_sync, "researchCommittee": committee}


@router.post("/publications/{publication_id}/committee/run")
def run_publication_committee(
    publication_id: str,
    payload: CommitteeRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_publisher(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    version = _selected_version(db, publication, payload.publication_version_id)
    committee = run_research_committee_for_publication(
        db,
        publication=publication,
        publication_version=version,
        user_id=user.id,
        commit=True,
    )
    write_audit_event(
        db,
        event_type="premium_research_committee_run",
        category="premium_research",
        action="run_committee",
        user_id=user.id,
        severity="warning" if committee["decision"] == "blocked" else "info",
        resource_type="research_committee_run",
        resource_id=committee["id"],
        message="Research Committee executado por endpoint administrativo protegido.",
        metadata={"publicationId": publication.id, "versionId": version.id, "decision": committee["decision"]},
    )
    return committee


@router.post("/publications/{publication_id}/attribution/run", status_code=status.HTTP_201_CREATED)
def run_publication_attribution(
    publication_id: str,
    payload: AttributionRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_publisher(db, user)
    if payload.start_date and payload.end_date and payload.start_date > payload.end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Data inicial maior que data final.")
    publication = _owned_publication(db, publication_id, user.id)
    version = _selected_version(db, publication, payload.publication_version_id)
    attribution = run_performance_attribution_for_publication(
        db,
        publication=publication,
        publication_version=version,
        user_id=user.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        benchmark_name=payload.benchmark_name,
        benchmark_return_pct=payload.benchmark_return_pct,
        refresh_market=payload.refresh_market,
        commit=True,
    )
    write_audit_event(
        db,
        event_type="premium_research_attribution_run",
        category="premium_research",
        action="run_performance_attribution",
        user_id=user.id,
        severity="info" if attribution["dataQualityScore"] >= 60 else "warning",
        resource_type="research_attribution_run",
        resource_id=attribution["id"],
        message="Performance Attribution executado para publicacao premium.",
        metadata={
            "publicationId": publication.id,
            "versionId": version.id,
            "period": attribution["period"],
            "portfolioReturnPct": attribution["portfolioReturnPct"],
            "dataQualityScore": attribution["dataQualityScore"],
        },
    )
    return attribution


@router.post("/publications/{publication_id}/reviews", status_code=status.HTTP_201_CREATED)
def review_publication(
    publication_id: str,
    payload: PublicationReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_reviewer(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    version = _selected_version(db, publication, payload.publication_version_id)
    review = PublicationReview(
        publication_id=publication.id,
        version_id=version.id,
        reviewer_user_id=user.id,
        decision=payload.decision,
        status="closed",
        comments=payload.comments,
        requested_changes_json=json.dumps(payload.requested_changes or [], ensure_ascii=False),
    )
    db.add(review)

    publication.reviewer_user_id = user.id
    publication.updated_at = datetime.now(UTC)
    if payload.decision == "approve":
        publication.status = "reviewed"
        version.status = "reviewed"
        for section in version.sections:
            if section.status != "blocked":
                section.status = "approved"
                section.approved_by_user_id = user.id
                section.approved_at = datetime.now(UTC)
                section.updated_at = datetime.now(UTC)
    elif payload.decision == "block":
        publication.status = "data_pending"
        version.status = "data_pending"
    else:
        publication.status = "draft"
        version.status = "draft"

    db.flush()
    db.commit()
    db.refresh(review)
    db.refresh(publication)
    write_audit_event(
        db,
        event_type="premium_research_review_recorded",
        category="premium_research",
        action="review_publication",
        user_id=user.id,
        severity="warning" if payload.decision != "approve" else "info",
        resource_type="publication_review",
        resource_id=review.id,
        message="Revisao humana registrada no fluxo premium.",
        metadata={
            "publicationId": publication.id,
            "versionId": version.id,
            "decision": payload.decision,
            "requestedChanges": payload.requested_changes,
        },
    )
    return {"publication": _publication_detail(publication), "review": _review_to_dict(review)}


@router.post("/publications/{publication_id}/approvals", status_code=status.HTTP_201_CREATED)
def approve_publication(
    publication_id: str,
    payload: PublicationApprovalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_approver(db, user)
    publication = _owned_publication(db, publication_id, user.id)
    version = _selected_version(db, publication, payload.publication_version_id)

    if payload.decision == "approve_publication":
        _assert_publication_can_be_approved(db, publication, version)

    approval = PublicationApproval(
        publication_id=publication.id,
        version_id=version.id,
        approver_user_id=user.id,
        decision=payload.decision,
        comments=payload.comments,
        approved_at=datetime.now(UTC) if payload.decision == "approve_publication" else None,
    )
    db.add(approval)

    publication.approver_user_id = user.id
    publication.updated_at = datetime.now(UTC)
    if payload.decision == "approve_publication":
        publication.status = "approved"
        version.status = "approved"
    else:
        publication.status = "draft"
        version.status = "draft"

    db.flush()
    db.commit()
    db.refresh(approval)
    db.refresh(publication)
    write_audit_event(
        db,
        event_type="premium_research_approval_recorded",
        category="premium_research",
        action="approve_publication",
        user_id=user.id,
        severity="info" if payload.decision == "approve_publication" else "warning",
        resource_type="publication_approval",
        resource_id=approval.id,
        message="Decisao de aprovacao humana registrada no fluxo premium.",
        metadata={
            "publicationId": publication.id,
            "versionId": version.id,
            "decision": payload.decision,
        },
    )
    return {"publication": _publication_detail(publication), "approval": _approval_to_dict(approval)}


@router.get("/committee/runs")
def list_committee_runs(
    limit: int = Query(default=50, ge=1, le=200),
    decision: str | None = Query(default=None, max_length=40),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    stmt = (
        select(ResearchCommitteeRun)
        .where(ResearchCommitteeRun.created_by_user_id == user.id)
        .order_by(desc(ResearchCommitteeRun.created_at))
        .limit(limit)
    )
    if decision:
        stmt = stmt.where(ResearchCommitteeRun.decision == decision)
    runs = list(db.execute(stmt).scalars().all())
    return {"items": [committee_run_to_dict(item, include_details=False) for item in runs], "count": len(runs), "limit": limit}


@router.get("/committee/runs/{run_id}")
def get_committee_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    run = _owned_committee_run(db, run_id, user.id)
    return committee_run_to_dict(run)


@router.get("/attribution/runs")
def list_attribution_runs(
    limit: int = Query(default=50, ge=1, le=200),
    period: str | None = Query(default=None, max_length=40),
    publication_id: str | None = Query(default=None, max_length=32),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    stmt = (
        select(ResearchAttributionRun)
        .where(ResearchAttributionRun.created_by_user_id == user.id)
        .order_by(desc(ResearchAttributionRun.created_at))
        .limit(limit)
    )
    if period:
        stmt = stmt.where(ResearchAttributionRun.period == period)
    if publication_id:
        stmt = stmt.where(ResearchAttributionRun.publication_id == publication_id)
    runs = list(db.execute(stmt).scalars().all())
    return {"items": [attribution_run_to_dict(item, include_assets=False) for item in runs], "count": len(runs), "limit": limit}


@router.get("/attribution/runs/{run_id}")
def get_attribution_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    run = _owned_attribution_run(db, run_id, user.id)
    return attribution_run_to_dict(run)


@router.get("/snapshots")
def list_snapshots(
    limit: int = Query(default=50, ge=1, le=200),
    period: str | None = Query(default=None, max_length=40),
    snapshot_type: str | None = Query(default=None, max_length=80),
    include_payload: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    stmt = (
        select(PublicationSnapshot)
        .join(ResearchPublication, PublicationSnapshot.publication_id == ResearchPublication.id)
        .where(_publication_visible_to_user(db, user))
        .order_by(desc(PublicationSnapshot.created_at))
        .limit(limit)
    )
    if period:
        stmt = stmt.where(PublicationSnapshot.period == period)
    if snapshot_type:
        stmt = stmt.where(PublicationSnapshot.snapshot_type == snapshot_type)
    rows = list(db.execute(stmt).scalars().all())
    return {
        "items": [snapshot_to_dict(row, include_payload=include_payload) for row in rows],
        "count": len(rows),
        "limit": limit,
    }


@router.post("/snapshots/{snapshot_id}/render", status_code=status.HTTP_201_CREATED)
def render_snapshot(
    snapshot_id: str,
    payload: PublicationRenderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_publisher(db, user)
    snapshot = _owned_snapshot(db, snapshot_id, user.id)
    try:
        rendered = render_publication_snapshot(
            db,
            snapshot=snapshot,
            user_id=user.id,
            artifact_type=payload.artifact_type,
            force=payload.force,
            commit=True,
        )
    except PublicationRenderError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    artifact = _owned_artifact(db, rendered["id"], user.id)
    result = artifact_to_dict(artifact, include_content=payload.include_content)
    result["alreadyExists"] = rendered.get("alreadyExists", False)
    write_audit_event(
        db,
        event_type="premium_research_artifact_rendered",
        category="premium_research",
        action="render_artifact",
        user_id=user.id,
        severity="info",
        resource_type="publication_artifact",
        resource_id=result["id"],
        message="Artefato HTML premium gerado a partir de snapshot imutavel.",
        metadata={
            "snapshotId": snapshot.id,
            "publicationId": snapshot.publication_id,
            "artifactHash": result["artifactHash"],
            "sourceSnapshotHash": result["sourceSnapshotHash"],
            "alreadyExists": result["alreadyExists"],
        },
    )
    return result


@router.get("/snapshots/{snapshot_id}/artifacts")
def list_snapshot_artifacts(
    snapshot_id: str,
    include_content: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    snapshot = _owned_snapshot(db, snapshot_id, user.id)
    rows = list(
        db.execute(
            select(PublicationArtifact)
            .where(PublicationArtifact.snapshot_id == snapshot.id)
            .order_by(desc(PublicationArtifact.created_at))
        )
        .scalars()
        .all()
    )
    return {
        "items": [artifact_to_dict(row, include_content=include_content) for row in rows],
        "count": len(rows),
    }


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(
    snapshot_id: str,
    include_payload: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    snapshot = _owned_snapshot(db, snapshot_id, user.id)
    return snapshot_to_dict(snapshot, include_payload=include_payload)


@router.get("/artifacts")
def list_artifacts(
    limit: int = Query(default=50, ge=1, le=200),
    period: str | None = Query(default=None, max_length=40),
    artifact_type: str | None = Query(default=None, max_length=80),
    include_content: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    stmt = (
        select(PublicationArtifact)
        .join(ResearchPublication, PublicationArtifact.publication_id == ResearchPublication.id)
        .where(_publication_visible_to_user(db, user))
        .order_by(desc(PublicationArtifact.created_at))
        .limit(limit)
    )
    if period:
        stmt = stmt.where(PublicationArtifact.period == period)
    if artifact_type:
        stmt = stmt.where(PublicationArtifact.artifact_type == artifact_type)
    rows = list(db.execute(stmt).scalars().all())
    return {
        "items": [artifact_to_dict(row, include_content=include_content) for row in rows],
        "count": len(rows),
        "limit": limit,
    }


@router.post("/artifacts/{artifact_id}/pdf", status_code=status.HTTP_201_CREATED)
def render_artifact_pdf(
    artifact_id: str,
    payload: PublicationPdfRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_publisher(db, user)
    html_artifact = _owned_artifact(db, artifact_id, user.id)
    try:
        rendered = render_pdf_from_html_artifact(
            db,
            html_artifact=html_artifact,
            user_id=user.id,
            force=payload.force,
            commit=True,
        )
    except PublicationPdfError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    pdf_artifact = _owned_artifact(db, rendered["id"], user.id)
    result = artifact_to_dict(pdf_artifact, include_content=False)
    result["alreadyExists"] = rendered.get("alreadyExists", False)
    result["downloadUrl"] = f"/api/premium/artifacts/{pdf_artifact.id}/download"
    write_audit_event(
        db,
        event_type="premium_research_pdf_rendered",
        category="premium_research",
        action="render_pdf",
        user_id=user.id,
        severity="info",
        resource_type="publication_artifact",
        resource_id=result["id"],
        message="PDF premium gerado a partir de artefato HTML aprovado.",
        metadata={
            "sourceArtifactId": html_artifact.id,
            "snapshotId": html_artifact.snapshot_id,
            "publicationId": html_artifact.publication_id,
            "artifactHash": result["artifactHash"],
            "sourceSnapshotHash": result["sourceSnapshotHash"],
            "alreadyExists": result["alreadyExists"],
        },
    )
    return result


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(
    artifact_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    artifact = _artifact_for_access(db, artifact_id)
    if artifact.content_type != "application/pdf" or not artifact.binary_content:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Artefato nao possui PDF binario para download.")
    editorial_owner = _is_publication_editorial_owner(artifact, user.id) or user_has_any_role(db, user_id=user.id, roles=ADMIN_ROLES)
    if not editorial_owner and artifact.publication.status not in {"approved", "published"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Publicacao premium ainda nao liberada.")
    authorization = authorize_premium_artifact_access(
        db,
        user_id=user.id,
        artifact=artifact,
        action=DOWNLOAD_ACTION,
        editorial_owner=editorial_owner,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        commit=True,
    )
    if not authorization["allowed"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seu plano atual nao permite baixar este PDF premium.")
    filename = _download_filename(artifact)
    return Response(
        content=artifact.binary_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Artifact-Hash": artifact.artifact_hash,
        },
    )


@router.get("/artifacts/{artifact_id}")
def get_artifact(
    artifact_id: str,
    include_content: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    artifact = _owned_artifact(db, artifact_id, user.id)
    return artifact_to_dict(artifact, include_content=include_content)


@router.get("/theses")
def list_thesis_versions(
    ticker: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    stmt = (
        select(AssetThesisVersion)
        .join(AssetThesis)
        .where(AssetThesisVersion.created_by_user_id == user.id)
        .order_by(desc(AssetThesisVersion.created_at))
        .limit(limit)
    )
    if ticker:
        stmt = stmt.where(AssetThesis.ticker == ticker.upper())
    versions = list(db.execute(stmt).scalars().all())
    return {"items": [thesis_version_to_dict(item) for item in versions], "count": len(versions), "limit": limit}


@router.get("/ratings")
def list_rating_versions(
    ticker: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editorial(db, user)
    stmt = (
        select(AssetRatingVersion)
        .join(AssetRating)
        .where(AssetRatingVersion.created_by_user_id == user.id)
        .order_by(desc(AssetRatingVersion.created_at))
        .limit(limit)
    )
    if ticker:
        stmt = stmt.where(AssetRating.ticker == ticker.upper())
    versions = list(db.execute(stmt).scalars().all())
    return {"items": [rating_version_to_dict(item) for item in versions], "count": len(versions), "limit": limit}


def _require_admin(db: Session, user: User) -> None:
    require_any_role(db, user, ADMIN_ROLES, detail="Apenas administradores podem executar esta acao premium.")


def _require_editorial(db: Session, user: User) -> None:
    require_any_role(db, user, EDITORIAL_ROLES, detail="Apenas usuarios editoriais podem acessar esta area.")


def _require_publisher(db: Session, user: User) -> None:
    require_any_role(db, user, PUBLISHER_ROLES, detail="Apenas administradores ou editores podem alterar publicacoes premium.")


def _require_reviewer(db: Session, user: User) -> None:
    require_any_role(db, user, REVIEW_ROLES, detail="Apenas administradores ou revisores podem registrar revisao.")


def _require_approver(db: Session, user: User) -> None:
    require_any_role(db, user, APPROVAL_ROLES, detail="Apenas administradores ou editores podem aprovar publicacoes premium.")


def _publication_visible_to_user(db: Session, user: User):
    if user_has_any_role(db, user_id=user.id, roles=ADMIN_ROLES):
        return true()
    return or_(
        ResearchPublication.author_user_id == user.id,
        ResearchPublication.reviewer_user_id == user.id,
        ResearchPublication.approver_user_id == user.id,
    )


def _owned_publication(db: Session, publication_id: str, user_id: str) -> ResearchPublication:
    user = db.get(User, user_id)
    publication = db.execute(
        select(ResearchPublication).where(
            ResearchPublication.id == publication_id,
            _publication_visible_to_user(db, user) if user else false(),
        )
    ).scalar_one_or_none()
    if publication is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publicacao premium nao encontrada.")
    return publication


def _publication_version(db: Session, publication: ResearchPublication, version_id: str) -> PublicationVersion:
    version = db.execute(
        select(PublicationVersion).where(
            PublicationVersion.id == version_id,
            PublicationVersion.publication_id == publication.id,
        )
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versao da publicacao nao encontrada.")
    return version


def _selected_version(db: Session, publication: ResearchPublication, version_id: str | None) -> PublicationVersion:
    if version_id:
        return _publication_version(db, publication, version_id)
    version = db.execute(
        select(PublicationVersion)
        .where(PublicationVersion.publication_id == publication.id)
        .order_by(desc(PublicationVersion.created_at))
        .limit(1)
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publicacao premium sem versao.")
    return version


def _owned_committee_run(db: Session, run_id: str, user_id: str) -> ResearchCommitteeRun:
    run = db.execute(
        select(ResearchCommitteeRun).where(
            ResearchCommitteeRun.id == run_id,
            ResearchCommitteeRun.created_by_user_id == user_id,
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rodada do comite nao encontrada.")
    return run


def _owned_attribution_run(db: Session, run_id: str, user_id: str) -> ResearchAttributionRun:
    run = db.execute(
        select(ResearchAttributionRun).where(
            ResearchAttributionRun.id == run_id,
            ResearchAttributionRun.created_by_user_id == user_id,
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rodada de atribuicao nao encontrada.")
    return run


def _owned_snapshot(db: Session, snapshot_id: str, user_id: str) -> PublicationSnapshot:
    user = db.get(User, user_id)
    snapshot = db.execute(
        select(PublicationSnapshot)
        .join(ResearchPublication, PublicationSnapshot.publication_id == ResearchPublication.id)
        .where(PublicationSnapshot.id == snapshot_id, _publication_visible_to_user(db, user) if user else false())
    ).scalar_one_or_none()
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot premium nao encontrado.")
    return snapshot


def _owned_artifact(db: Session, artifact_id: str, user_id: str) -> PublicationArtifact:
    user = db.get(User, user_id)
    artifact = db.execute(
        select(PublicationArtifact)
        .join(ResearchPublication, PublicationArtifact.publication_id == ResearchPublication.id)
        .where(PublicationArtifact.id == artifact_id, _publication_visible_to_user(db, user) if user else false())
    ).scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefato premium nao encontrado.")
    return artifact


def _subscriber_home(db: Session, user: User, *, limit: int) -> dict[str, Any]:
    access = list_user_premium_access(db, user_id=user.id)
    rbac = rbac_summary(db, user_id=user.id)
    active_keys = {item.get("entitlementKey") for item in access.get("activeEntitlements", [])}
    role_names = set(rbac.get("roleNames", []))
    editorial_access = bool(role_names & EDITORIAL_ROLES)
    can_read_premium = editorial_access or "premium.research.read" in active_keys or "premium.research.admin" in active_keys

    publications = list(
        db.execute(
            select(ResearchPublication)
            .where(ResearchPublication.status.in_(("approved", "published")))
            .order_by(desc(ResearchPublication.published_at), desc(ResearchPublication.created_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )

    edition_rows = []
    total_pdfs = 0
    available_downloads = 0
    for publication in publications:
        pdf_artifacts = list(
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
            .all()
        )
        artifacts = []
        for artifact in pdf_artifacts:
            total_pdfs += 1
            editorial_owner = _is_publication_editorial_owner(artifact, user.id) or user_has_any_role(db, user_id=user.id, roles=ADMIN_ROLES)
            inspection = inspect_premium_artifact_access(
                db,
                user_id=user.id,
                artifact=artifact,
                action=DOWNLOAD_ACTION,
                editorial_owner=editorial_owner,
            )
            can_download = bool(inspection.get("allowed"))
            if can_download:
                available_downloads += 1
            artifacts.append(
                {
                    **artifact_to_dict(artifact, include_content=False),
                    "downloadUrl": f"/api/premium/artifacts/{artifact.id}/download",
                    "canDownload": can_download,
                    "accessReason": inspection.get("reason"),
                    "accessEntitlement": inspection.get("entitlement"),
                }
            )

        edition_rows.append(
            {
                "id": publication.id,
                "period": publication.period,
                "title": publication.title,
                "subtitle": publication.subtitle,
                "status": publication.status,
                "version": publication.version,
                "confidence": _number(publication.confidence),
                "publishedAt": publication.published_at.isoformat() if publication.published_at else "",
                "createdAt": publication.created_at.isoformat() if publication.created_at else "",
                "canRead": can_read_premium,
                "pdfArtifacts": artifacts,
                "pdfCount": len(artifacts),
            }
        )

    active_subscription = next(
        (item for item in access.get("subscriptions", []) if item.get("status") in {"active", "trialing"}),
        None,
    )
    logs = list_premium_access_logs(db, user_id=user.id, limit=20)
    delivery_inbox = list_subscriber_delivery_inbox(db, user=user, limit=80)
    return {
        "rbac": rbac,
        "access": access,
        "activeSubscription": active_subscription,
        "canReadPremium": can_read_premium,
        "editions": edition_rows,
        "editionCount": len(edition_rows),
        "pdfCount": total_pdfs,
        "availableDownloadCount": available_downloads,
        "deliveryInbox": delivery_inbox,
        "recentAccessLogs": logs.get("items", []),
    }


def _artifact_for_access(db: Session, artifact_id: str) -> PublicationArtifact:
    artifact = db.execute(select(PublicationArtifact).where(PublicationArtifact.id == artifact_id)).scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefato premium nao encontrado.")
    return artifact


def _is_publication_editorial_owner(artifact: PublicationArtifact, user_id: str) -> bool:
    publication = artifact.publication
    return bool(
        publication
        and (
            publication.author_user_id == user_id
            or publication.reviewer_user_id == user_id
            or publication.approver_user_id == user_id
        )
    )


def _download_filename(artifact: PublicationArtifact) -> str:
    base = "".join(ch.lower() if ch.isalnum() else "-" for ch in artifact.title or "carteira-alpha-premium")
    base = "-".join(part for part in base.split("-") if part)[:80] or "carteira-alpha-premium"
    suffix = artifact.period.replace("/", "-").replace(" ", "-") if artifact.period else artifact.id[:8]
    return f"{base}-{suffix}.pdf"


def _publication_detail(publication: ResearchPublication) -> dict[str, Any]:
    payload = publication_to_dict(publication)
    payload["versions"] = [
        _version_summary(item)
        for item in sorted(publication.versions, key=_created_sort_value, reverse=True)
    ]
    payload["committeeRuns"] = [
        committee_run_to_dict(item, include_details=False)
        for item in sorted(publication.committee_runs, key=_created_sort_value, reverse=True)
    ]
    payload["attributionRuns"] = [
        attribution_run_to_dict(item, include_assets=False)
        for item in sorted(publication.attribution_runs, key=_created_sort_value, reverse=True)
    ]
    payload["snapshots"] = [
        snapshot_to_dict(item, include_payload=False)
        for item in sorted(publication.snapshots, key=_created_sort_value, reverse=True)
    ]
    payload["artifacts"] = [
        artifact_to_dict(item, include_content=False)
        for item in sorted(publication.artifacts, key=_created_sort_value, reverse=True)
    ]
    payload["reviews"] = [
        _review_to_dict(item)
        for item in sorted(publication.reviews, key=_created_sort_value, reverse=True)
    ]
    payload["approvals"] = [
        _approval_to_dict(item)
        for item in sorted(publication.approvals, key=_created_sort_value, reverse=True)
    ]
    return payload


def _version_detail(version: PublicationVersion) -> dict[str, Any]:
    payload = _version_summary(version)
    payload["payload"] = _json_load(version.payload_json, {})
    payload["changelog"] = _json_load(version.changelog_json, [])
    payload["sections"] = [
        {
            "id": item.id,
            "key": item.section_key,
            "title": item.title,
            "order": item.section_order,
            "status": item.status,
            "confidence": _number(item.confidence),
            "dataGaps": _json_load(item.data_gaps_json, []),
            "evidenceIds": _json_load(item.evidence_ids_json, []),
            "requiresHumanApproval": item.requires_human_approval,
        }
        for item in sorted(version.sections, key=lambda row: row.section_order)
    ]
    return payload


def _version_summary(version: PublicationVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "publicationId": version.publication_id,
        "version": version.version,
        "status": version.status,
        "versionHash": version.version_hash,
        "readinessScore": _number(version.readiness_score),
        "readinessClassification": version.readiness_classification,
        "sourceCount": version.source_count,
        "partialDataCount": version.partial_data_count,
        "fallbackCount": version.fallback_count,
        "createdByUserId": version.created_by_user_id,
        "createdAt": version.created_at.isoformat() if version.created_at else "",
    }


def _json_load(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw or "")
    except Exception:
        return fallback


def _number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _created_sort_value(row: Any) -> datetime:
    return getattr(row, "created_at", None) or datetime.min


def _review_to_dict(review: PublicationReview) -> dict[str, Any]:
    return {
        "id": review.id,
        "publicationId": review.publication_id,
        "versionId": review.version_id,
        "reviewerUserId": review.reviewer_user_id,
        "decision": review.decision,
        "status": review.status,
        "comments": review.comments,
        "requestedChanges": _json_load(review.requested_changes_json, []),
        "createdAt": review.created_at.isoformat() if review.created_at else "",
    }


def _approval_to_dict(approval: PublicationApproval) -> dict[str, Any]:
    return {
        "id": approval.id,
        "publicationId": approval.publication_id,
        "versionId": approval.version_id,
        "approverUserId": approval.approver_user_id,
        "decision": approval.decision,
        "comments": approval.comments,
        "approvedAt": approval.approved_at.isoformat() if approval.approved_at else "",
        "createdAt": approval.created_at.isoformat() if approval.created_at else "",
    }


def _assert_publication_can_be_approved(db: Session, publication: ResearchPublication, version: PublicationVersion) -> None:
    approved_review = db.execute(
        select(PublicationReview)
        .where(
            PublicationReview.publication_id == publication.id,
            PublicationReview.version_id == version.id,
            PublicationReview.decision == "approve",
        )
        .order_by(desc(PublicationReview.created_at))
        .limit(1)
    ).scalar_one_or_none()
    if approved_review is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A publicacao precisa de revisao humana aprovada antes da aprovacao final.",
        )

    latest_committee = db.execute(
        select(ResearchCommitteeRun)
        .where(
            ResearchCommitteeRun.publication_id == publication.id,
            ResearchCommitteeRun.publication_version_id == version.id,
        )
        .order_by(desc(ResearchCommitteeRun.created_at))
        .limit(1)
    ).scalar_one_or_none()
    if latest_committee is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Execute o Research Committee antes da aprovacao final.",
        )
    if latest_committee.decision == "blocked" or latest_committee.blocker_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O Research Committee bloqueou esta versao. Corrija os bloqueios antes da aprovacao.",
        )
