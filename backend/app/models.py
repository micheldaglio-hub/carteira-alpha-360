from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    roles: Mapped[list[UserRole]] = relationship(
        foreign_keys="UserRole.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    granted_roles: Mapped[list[UserRole]] = relationship(
        foreign_keys="UserRole.granted_by_user_id",
        back_populates="granted_by_user",
    )
    transactions: Mapped[list[Transaction]] = relationship(back_populates="user", cascade="all, delete-orphan")
    dividends: Mapped[list[Dividend]] = relationship(back_populates="user", cascade="all, delete-orphan")
    targets: Mapped[list[TargetAllocation]] = relationship(back_populates="user", cascade="all, delete-orphan")
    alerts: Mapped[list[Alert]] = relationship(back_populates="user", cascade="all, delete-orphan")
    alpha_events: Mapped[list[AlphaEventModel]] = relationship(back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped[list[UserPreference]] = relationship(back_populates="user", cascade="all, delete-orphan")
    subscriptions: Mapped[list[UserSubscription]] = relationship(back_populates="user", cascade="all, delete-orphan")
    premium_entitlements: Mapped[list[PremiumEntitlement]] = relationship(back_populates="user", cascade="all, delete-orphan")
    premium_access_logs: Mapped[list[PremiumAccessLog]] = relationship(back_populates="user", cascade="all, delete-orphan")
    billing_checkout_sessions: Mapped[list[BillingCheckoutSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    billing_transactions: Mapped[list[BillingTransaction]] = relationship(back_populates="user", cascade="all, delete-orphan")
    distribution_recipients: Mapped[list[DistributionRecipient]] = relationship(back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role", "scope_type", "scope_id", name="uq_user_roles_scope"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(80), index=True)
    scope_type: Mapped[str] = mapped_column(String(40), default="global", index=True)
    scope_id: Mapped[str] = mapped_column(String(120), default="*", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    source: Mapped[str] = mapped_column(String(80), default="manual", index=True)
    granted_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(
        foreign_keys=[user_id],
        back_populates="roles",
    )
    granted_by_user: Mapped[User | None] = relationship(
        foreign_keys=[granted_by_user_id],
        back_populates="granted_roles",
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(32), default="user", index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(24), default="info", index=True)
    action: Mapped[str] = mapped_column(String(120), default="", index=True)
    resource_type: Mapped[str] = mapped_column(String(80), default="", index=True)
    resource_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    request_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    ip_address: Mapped[str] = mapped_column(String(80), default="")
    user_agent: Mapped[str] = mapped_column(String(240), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    job_name: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    rows_affected: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")


class DataEvidenceLedger(Base):
    __tablename__ = "data_evidence_ledger"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    evidence_key: Mapped[str] = mapped_column(String(160), index=True)
    domain: Mapped[str] = mapped_column(String(80), index=True)
    field_name: Mapped[str] = mapped_column(String(120), index=True)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    value_text: Mapped[str] = mapped_column(Text, default="")
    currency: Mapped[str] = mapped_column(String(8), default="")
    unit: Mapped[str] = mapped_column(String(32), default="")
    provider: Mapped[str] = mapped_column(String(80), default="", index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="", index=True)
    source_ref: Mapped[str] = mapped_column(String(240), default="")
    formula_name: Mapped[str] = mapped_column(String(120), default="", index=True)
    formula_version: Mapped[str] = mapped_column(String(40), default="")
    input_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    quality_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    status: Mapped[str] = mapped_column(String(32), default="ok", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ResearchPublication(Base):
    __tablename__ = "research_publications"
    __table_args__ = (
        UniqueConstraint("publication_type", "period", "version", name="uq_research_publication_period_version"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_type: Mapped[str] = mapped_column(String(80), default="monthly_research", index=True)
    period: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(220))
    subtitle: Mapped[str] = mapped_column(Text, default="")
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    version: Mapped[str] = mapped_column(String(32), default="v0.1", index=True)
    author_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    approver_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    partial_data_count: Mapped[int] = mapped_column(Integer, default=0)
    fallback_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    legal_disclaimer: Mapped[str] = mapped_column(Text, default="")
    version_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    changelog_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    versions: Mapped[list[PublicationVersion]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    sections: Mapped[list[PublicationSection]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    assets: Mapped[list[PublicationAsset]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    sources: Mapped[list[PublicationSource]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    evidence_links: Mapped[list[PublicationEvidence]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    reviews: Mapped[list[PublicationReview]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    approvals: Mapped[list[PublicationApproval]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    corrections: Mapped[list[PublicationCorrection]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    committee_runs: Mapped[list[ResearchCommitteeRun]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    attribution_runs: Mapped[list[ResearchAttributionRun]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    snapshots: Mapped[list[PublicationSnapshot]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    artifacts: Mapped[list[PublicationArtifact]] = relationship(back_populates="publication", cascade="all, delete-orphan")
    distribution_campaigns: Mapped[list[DistributionCampaign]] = relationship(back_populates="publication", cascade="all, delete-orphan")


class PublicationVersion(Base):
    __tablename__ = "publication_versions"
    __table_args__ = (
        UniqueConstraint("publication_id", "version", name="uq_publication_version_scope"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    version: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    version_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    readiness_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    readiness_classification: Mapped[str] = mapped_column(String(40), default="incomplete", index=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    partial_data_count: Mapped[int] = mapped_column(Integer, default=0)
    fallback_count: Mapped[int] = mapped_column(Integer, default=0)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    changelog_json: Mapped[str] = mapped_column(Text, default="[]")
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication] = relationship(back_populates="versions")
    sections: Mapped[list[PublicationSection]] = relationship(back_populates="version", cascade="all, delete-orphan")
    committee_runs: Mapped[list[ResearchCommitteeRun]] = relationship(back_populates="publication_version", cascade="all, delete-orphan")
    attribution_runs: Mapped[list[ResearchAttributionRun]] = relationship(back_populates="publication_version", cascade="all, delete-orphan")
    snapshots: Mapped[list[PublicationSnapshot]] = relationship(back_populates="publication_version", cascade="all, delete-orphan")
    artifacts: Mapped[list[PublicationArtifact]] = relationship(back_populates="publication_version", cascade="all, delete-orphan")


class PublicationSection(Base):
    __tablename__ = "publication_sections"
    __table_args__ = (
        UniqueConstraint("version_id", "section_key", name="uq_publication_section_version_key"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("publication_versions.id"), index=True)
    section_key: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(220))
    section_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    content_json: Mapped[str] = mapped_column(Text, default="{}")
    data_gaps_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    approved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    publication: Mapped[ResearchPublication] = relationship(back_populates="sections")
    version: Mapped[PublicationVersion] = relationship(back_populates="sections")
    evidence_links: Mapped[list[PublicationEvidence]] = relationship(back_populates="section", cascade="all, delete-orphan")


class PublicationAsset(Base):
    __tablename__ = "publication_assets"
    __table_args__ = (
        UniqueConstraint("version_id", "asset_id", name="uq_publication_asset_version_asset"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("publication_versions.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    ticker: Mapped[str] = mapped_column(String(32), default="", index=True)
    asset_name: Mapped[str] = mapped_column(String(180), default="")
    role: Mapped[str] = mapped_column(String(120), default="")
    action: Mapped[str] = mapped_column(String(40), default="maintain", index=True)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    previous_weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    rating: Mapped[str] = mapped_column(String(40), default="", index=True)
    thesis_status: Mapped[str] = mapped_column(String(40), default="", index=True)
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication] = relationship(back_populates="assets")
    version: Mapped[PublicationVersion] = relationship()
    asset: Mapped[Asset | None] = relationship()


class PublicationSource(Base):
    __tablename__ = "publication_sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    version_id: Mapped[str | None] = mapped_column(ForeignKey("publication_versions.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="", index=True)
    provider: Mapped[str] = mapped_column(String(80), default="", index=True)
    source_ref: Mapped[str] = mapped_column(String(240), default="", index=True)
    title: Mapped[str] = mapped_column(String(220), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    status: Mapped[str] = mapped_column(String(32), default="ok", index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication] = relationship(back_populates="sources")
    version: Mapped[PublicationVersion | None] = relationship()


class PublicationEvidence(Base):
    __tablename__ = "publication_evidence"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    version_id: Mapped[str | None] = mapped_column(ForeignKey("publication_versions.id"), nullable=True, index=True)
    section_id: Mapped[str | None] = mapped_column(ForeignKey("publication_sections.id"), nullable=True, index=True)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("data_evidence_ledger.id"), nullable=True, index=True)
    evidence_key: Mapped[str] = mapped_column(String(160), default="", index=True)
    domain: Mapped[str] = mapped_column(String(80), default="", index=True)
    field_name: Mapped[str] = mapped_column(String(120), default="", index=True)
    provider: Mapped[str] = mapped_column(String(80), default="", index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="", index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    status: Mapped[str] = mapped_column(String(32), default="ok", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication] = relationship(back_populates="evidence_links")
    version: Mapped[PublicationVersion | None] = relationship()
    section: Mapped[PublicationSection | None] = relationship(back_populates="evidence_links")
    evidence: Mapped[DataEvidenceLedger | None] = relationship()


class PublicationReview(Base):
    __tablename__ = "publication_reviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("publication_versions.id"), index=True)
    reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(40), default="request_changes", index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    comments: Mapped[str] = mapped_column(Text, default="")
    requested_changes_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication] = relationship(back_populates="reviews")
    version: Mapped[PublicationVersion] = relationship()


class PublicationApproval(Base):
    __tablename__ = "publication_approvals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("publication_versions.id"), index=True)
    approver_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(40), default="reject_publication", index=True)
    comments: Mapped[str] = mapped_column(Text, default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication] = relationship(back_populates="approvals")
    version: Mapped[PublicationVersion] = relationship()


class PublicationCorrection(Base):
    __tablename__ = "publication_corrections"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("publication_versions.id"), index=True)
    previous_version: Mapped[str] = mapped_column(String(32), default="")
    new_version: Mapped[str] = mapped_column(String(32), default="")
    correction_type: Mapped[str] = mapped_column(String(60), default="", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    impact: Mapped[str] = mapped_column(Text, default="")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    approved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication] = relationship(back_populates="corrections")
    version: Mapped[PublicationVersion] = relationship()


class AssetThesis(Base):
    __tablename__ = "asset_theses"
    __table_args__ = (
        UniqueConstraint("ticker", "asset_class", "thesis_type", name="uq_asset_thesis_scope"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    universal_symbol: Mapped[str] = mapped_column(String(96), default="", index=True)
    asset_name: Mapped[str] = mapped_column(String(180), default="")
    asset_class: Mapped[str] = mapped_column(String(80), default="", index=True)
    thesis_type: Mapped[str] = mapped_column(String(80), default="recommended_portfolio", index=True)
    strategy_profile: Mapped[str] = mapped_column(String(80), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    current_version: Mapped[str] = mapped_column(String(32), default="", index=True)
    current_version_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    current_version_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    risk_level: Mapped[str] = mapped_column(String(40), default="", index=True)
    source_engine: Mapped[str] = mapped_column(String(120), default="", index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    next_review_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset | None] = relationship()
    versions: Mapped[list[AssetThesisVersion]] = relationship(back_populates="thesis", cascade="all, delete-orphan")
    evidence_links: Mapped[list[AssetThesisEvidence]] = relationship(back_populates="thesis", cascade="all, delete-orphan")


class AssetThesisVersion(Base):
    __tablename__ = "asset_thesis_versions"
    __table_args__ = (
        UniqueConstraint("thesis_id", "version", name="uq_asset_thesis_version_scope"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    thesis_id: Mapped[str] = mapped_column(ForeignKey("asset_theses.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    publication_id: Mapped[str | None] = mapped_column(ForeignKey("research_publications.id"), nullable=True, index=True)
    publication_version_id: Mapped[str | None] = mapped_column(ForeignKey("publication_versions.id"), nullable=True, index=True)
    version: Mapped[str] = mapped_column(String(32), index=True)
    version_hash: Mapped[str] = mapped_column(String(80), index=True)
    thesis_status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    role: Mapped[str] = mapped_column(String(160), default="")
    thesis_text: Mapped[str] = mapped_column(Text, default="")
    evidence_summary: Mapped[str] = mapped_column(Text, default="")
    risk_summary: Mapped[str] = mapped_column(Text, default="")
    monitoring_plan: Mapped[str] = mapped_column(Text, default="")
    invalidation_triggers_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    source_report_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    source_engine: Mapped[str] = mapped_column(String(120), default="", index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    conviction: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    risk_level: Mapped[str] = mapped_column(String(40), default="", index=True)
    data_quality: Mapped[str] = mapped_column(String(40), default="", index=True)
    change_reason: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    thesis: Mapped[AssetThesis] = relationship(back_populates="versions")
    asset: Mapped[Asset | None] = relationship()
    publication: Mapped[ResearchPublication | None] = relationship()
    publication_version: Mapped[PublicationVersion | None] = relationship()
    evidence_links: Mapped[list[AssetThesisEvidence]] = relationship(back_populates="thesis_version", cascade="all, delete-orphan")


class AssetThesisEvidence(Base):
    __tablename__ = "asset_thesis_evidence"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    thesis_id: Mapped[str] = mapped_column(ForeignKey("asset_theses.id"), index=True)
    thesis_version_id: Mapped[str] = mapped_column(ForeignKey("asset_thesis_versions.id"), index=True)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("data_evidence_ledger.id"), nullable=True, index=True)
    evidence_key: Mapped[str] = mapped_column(String(160), default="", index=True)
    domain: Mapped[str] = mapped_column(String(80), default="", index=True)
    field_name: Mapped[str] = mapped_column(String(120), default="", index=True)
    provider: Mapped[str] = mapped_column(String(80), default="", index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="", index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    status: Mapped[str] = mapped_column(String(32), default="ok", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    thesis: Mapped[AssetThesis] = relationship(back_populates="evidence_links")
    thesis_version: Mapped[AssetThesisVersion] = relationship(back_populates="evidence_links")
    evidence: Mapped[DataEvidenceLedger | None] = relationship()


class AssetRating(Base):
    __tablename__ = "asset_ratings"
    __table_args__ = (
        UniqueConstraint("ticker", "asset_class", "rating_type", name="uq_asset_rating_scope"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    thesis_id: Mapped[str | None] = mapped_column(ForeignKey("asset_theses.id"), nullable=True, index=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    asset_name: Mapped[str] = mapped_column(String(180), default="")
    asset_class: Mapped[str] = mapped_column(String(80), default="", index=True)
    rating_type: Mapped[str] = mapped_column(String(80), default="institutional", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    current_version: Mapped[str] = mapped_column(String(32), default="", index=True)
    current_version_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    current_version_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    current_rating: Mapped[str] = mapped_column(String(40), default="", index=True)
    current_classification: Mapped[str] = mapped_column(String(80), default="", index=True)
    current_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    risk_level: Mapped[str] = mapped_column(String(40), default="", index=True)
    source_engine: Mapped[str] = mapped_column(String(120), default="", index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    next_review_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset | None] = relationship()
    thesis: Mapped[AssetThesis | None] = relationship()
    versions: Mapped[list[AssetRatingVersion]] = relationship(back_populates="rating_parent", cascade="all, delete-orphan")
    evidence_links: Mapped[list[AssetRatingEvidence]] = relationship(back_populates="rating", cascade="all, delete-orphan")


class AssetRatingVersion(Base):
    __tablename__ = "asset_rating_versions"
    __table_args__ = (
        UniqueConstraint("rating_id", "version", name="uq_asset_rating_version_scope"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    rating_id: Mapped[str] = mapped_column(ForeignKey("asset_ratings.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    thesis_id: Mapped[str | None] = mapped_column(ForeignKey("asset_theses.id"), nullable=True, index=True)
    thesis_version_id: Mapped[str | None] = mapped_column(ForeignKey("asset_thesis_versions.id"), nullable=True, index=True)
    publication_id: Mapped[str | None] = mapped_column(ForeignKey("research_publications.id"), nullable=True, index=True)
    publication_version_id: Mapped[str | None] = mapped_column(ForeignKey("publication_versions.id"), nullable=True, index=True)
    version: Mapped[str] = mapped_column(String(32), index=True)
    version_hash: Mapped[str] = mapped_column(String(80), index=True)
    rating: Mapped[str] = mapped_column(String(40), default="", index=True)
    classification: Mapped[str] = mapped_column(String(80), default="", index=True)
    rating_status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    score_final: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    thesis_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    evidence_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    conviction_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    data_quality_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    governance_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    suitability_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    risk_level: Mapped[str] = mapped_column(String(40), default="", index=True)
    data_quality: Mapped[str] = mapped_column(String(40), default="", index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    strengths_json: Mapped[str] = mapped_column(Text, default="[]")
    watchpoints_json: Mapped[str] = mapped_column(Text, default="[]")
    limits_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    methodology_version: Mapped[str] = mapped_column(String(40), default="", index=True)
    source_engine: Mapped[str] = mapped_column(String(120), default="", index=True)
    source_thesis_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    change_reason: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    rating_parent: Mapped[AssetRating] = relationship(back_populates="versions")
    asset: Mapped[Asset | None] = relationship()
    thesis: Mapped[AssetThesis | None] = relationship()
    thesis_version: Mapped[AssetThesisVersion | None] = relationship()
    publication: Mapped[ResearchPublication | None] = relationship()
    publication_version: Mapped[PublicationVersion | None] = relationship()
    evidence_links: Mapped[list[AssetRatingEvidence]] = relationship(back_populates="rating_version", cascade="all, delete-orphan")


class AssetRatingEvidence(Base):
    __tablename__ = "asset_rating_evidence"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    rating_id: Mapped[str] = mapped_column(ForeignKey("asset_ratings.id"), index=True)
    rating_version_id: Mapped[str] = mapped_column(ForeignKey("asset_rating_versions.id"), index=True)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("data_evidence_ledger.id"), nullable=True, index=True)
    evidence_key: Mapped[str] = mapped_column(String(160), default="", index=True)
    domain: Mapped[str] = mapped_column(String(80), default="", index=True)
    field_name: Mapped[str] = mapped_column(String(120), default="", index=True)
    provider: Mapped[str] = mapped_column(String(80), default="", index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="", index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    status: Mapped[str] = mapped_column(String(32), default="ok", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    rating: Mapped[AssetRating] = relationship(back_populates="evidence_links")
    rating_version: Mapped[AssetRatingVersion] = relationship(back_populates="evidence_links")
    evidence: Mapped[DataEvidenceLedger | None] = relationship()


class ResearchCommitteeRun(Base):
    __tablename__ = "research_committee_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str | None] = mapped_column(ForeignKey("research_publications.id"), nullable=True, index=True)
    publication_version_id: Mapped[str | None] = mapped_column(ForeignKey("publication_versions.id"), nullable=True, index=True)
    period: Mapped[str] = mapped_column(String(40), default="", index=True)
    committee_type: Mapped[str] = mapped_column(String(80), default="premium_research", index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    decision: Mapped[str] = mapped_column(String(40), default="needs_review", index=True)
    readiness_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    approval_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    blocker_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    gate_count: Mapped[int] = mapped_column(Integer, default=0)
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    source_engine: Mapped[str] = mapped_column(String(120), default="research_committee", index=True)
    methodology_version: Mapped[str] = mapped_column(String(40), default="", index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    blockers_json: Mapped[str] = mapped_column(Text, default="[]")
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    publication: Mapped[ResearchPublication | None] = relationship(back_populates="committee_runs")
    publication_version: Mapped[PublicationVersion | None] = relationship(back_populates="committee_runs")
    gate_results: Mapped[list[ResearchCommitteeGateResult]] = relationship(back_populates="run", cascade="all, delete-orphan")
    votes: Mapped[list[ResearchCommitteeVote]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ResearchCommitteeGateResult(Base):
    __tablename__ = "research_committee_gate_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("research_committee_runs.id"), index=True)
    gate_key: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(220), default="")
    status: Mapped[str] = mapped_column(String(24), default="warn", index=True)
    severity: Mapped[str] = mapped_column(String(24), default="medium", index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    weight: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    reading: Mapped[str] = mapped_column(Text, default="")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    run: Mapped[ResearchCommitteeRun] = relationship(back_populates="gate_results")


class ResearchCommitteeVote(Base):
    __tablename__ = "research_committee_votes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("research_committee_runs.id"), index=True)
    voter_key: Mapped[str] = mapped_column(String(80), index=True)
    voter_type: Mapped[str] = mapped_column(String(80), default="engine", index=True)
    decision: Mapped[str] = mapped_column(String(40), default="request_changes", index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    weight: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    run: Mapped[ResearchCommitteeRun] = relationship(back_populates="votes")


class ResearchAttributionRun(Base):
    __tablename__ = "research_attribution_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str | None] = mapped_column(ForeignKey("research_publications.id"), nullable=True, index=True)
    publication_version_id: Mapped[str | None] = mapped_column(ForeignKey("publication_versions.id"), nullable=True, index=True)
    period: Mapped[str] = mapped_column(String(40), default="", index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    benchmark_name: Mapped[str] = mapped_column(String(120), default="", index=True)
    portfolio_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    benchmark_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    excess_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    price_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    income_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    data_quality_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    source_engine: Mapped[str] = mapped_column(String(120), default="performance_attribution", index=True)
    methodology_version: Mapped[str] = mapped_column(String(40), default="", index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    top_contributors_json: Mapped[str] = mapped_column(Text, default="[]")
    detractors_json: Mapped[str] = mapped_column(Text, default="[]")
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication | None] = relationship(back_populates="attribution_runs")
    publication_version: Mapped[PublicationVersion | None] = relationship(back_populates="attribution_runs")
    asset_rows: Mapped[list[ResearchAttributionAsset]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ResearchAttributionAsset(Base):
    __tablename__ = "research_attribution_assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("research_attribution_runs.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    ticker: Mapped[str] = mapped_column(String(32), default="", index=True)
    asset_name: Mapped[str] = mapped_column(String(180), default="")
    asset_class: Mapped[str] = mapped_column(String(80), default="", index=True)
    sector: Mapped[str] = mapped_column(String(120), default="", index=True)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    start_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    end_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    price_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    income_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    total_return_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    contribution_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    data_quality_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    provider: Mapped[str] = mapped_column(String(80), default="", index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="ok", index=True)
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    run: Mapped[ResearchAttributionRun] = relationship(back_populates="asset_rows")
    asset: Mapped[Asset | None] = relationship()


class PublicationSnapshot(Base):
    __tablename__ = "publication_snapshots"
    __table_args__ = (
        UniqueConstraint("publication_version_id", "snapshot_type", name="uq_publication_snapshot_version_type"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    publication_version_id: Mapped[str] = mapped_column(ForeignKey("publication_versions.id"), index=True)
    period: Mapped[str] = mapped_column(String(40), default="", index=True)
    snapshot_type: Mapped[str] = mapped_column(String(80), default="approved_edition", index=True)
    status: Mapped[str] = mapped_column(String(32), default="locked", index=True)
    version_label: Mapped[str] = mapped_column(String(32), default="", index=True)
    publication_status: Mapped[str] = mapped_column(String(32), default="", index=True)
    version_status: Mapped[str] = mapped_column(String(32), default="", index=True)
    snapshot_hash: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    source_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    evidence_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    approval_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    committee_run_id: Mapped[str | None] = mapped_column(ForeignKey("research_committee_runs.id"), nullable=True, index=True)
    attribution_run_id: Mapped[str | None] = mapped_column(ForeignKey("research_attribution_runs.id"), nullable=True, index=True)
    review_id: Mapped[str | None] = mapped_column(ForeignKey("publication_reviews.id"), nullable=True, index=True)
    approval_id: Mapped[str | None] = mapped_column(ForeignKey("publication_approvals.id"), nullable=True, index=True)
    section_count: Mapped[int] = mapped_column(Integer, default=0)
    asset_count: Mapped[int] = mapped_column(Integer, default=0)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    manifest_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication] = relationship(back_populates="snapshots")
    publication_version: Mapped[PublicationVersion] = relationship(back_populates="snapshots")
    committee_run: Mapped[ResearchCommitteeRun | None] = relationship()
    attribution_run: Mapped[ResearchAttributionRun | None] = relationship()
    review: Mapped[PublicationReview | None] = relationship()
    approval: Mapped[PublicationApproval | None] = relationship()
    artifacts: Mapped[list[PublicationArtifact]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")


class PublicationArtifact(Base):
    __tablename__ = "publication_artifacts"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "artifact_type", "render_version", name="uq_publication_artifact_snapshot_type_version"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    publication_version_id: Mapped[str] = mapped_column(ForeignKey("publication_versions.id"), index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("publication_snapshots.id"), index=True)
    period: Mapped[str] = mapped_column(String(40), default="", index=True)
    artifact_type: Mapped[str] = mapped_column(String(80), default="html", index=True)
    status: Mapped[str] = mapped_column(String(32), default="rendered", index=True)
    title: Mapped[str] = mapped_column(String(220), default="")
    content_type: Mapped[str] = mapped_column(String(120), default="text/html; charset=utf-8", index=True)
    file_extension: Mapped[str] = mapped_column(String(16), default="html")
    render_engine: Mapped[str] = mapped_column(String(120), default="publication_render_engine", index=True)
    render_version: Mapped[str] = mapped_column(String(40), default="", index=True)
    source_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("publication_artifacts.id"), nullable=True, index=True)
    source_snapshot_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    artifact_hash: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    html_content: Mapped[str] = mapped_column(Text, default="")
    binary_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    plain_text: Mapped[str] = mapped_column(Text, default="")
    content_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    manifest_json: Mapped[str] = mapped_column(Text, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    publication: Mapped[ResearchPublication] = relationship(back_populates="artifacts")
    publication_version: Mapped[PublicationVersion] = relationship(back_populates="artifacts")
    snapshot: Mapped[PublicationSnapshot] = relationship(back_populates="artifacts")
    source_artifact: Mapped[PublicationArtifact | None] = relationship(remote_side=[id])
    access_logs: Mapped[list[PremiumAccessLog]] = relationship(back_populates="artifact", cascade="all, delete-orphan")
    distribution_campaigns: Mapped[list[DistributionCampaign]] = relationship(back_populates="artifact")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    tier: Mapped[str] = mapped_column(String(40), default="free", index=True)
    currency: Mapped[str] = mapped_column(String(8), default="BRL")
    monthly_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    annual_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    features_json: Mapped[str] = mapped_column(Text, default="[]")
    limits_json: Mapped[str] = mapped_column(Text, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscriptions: Mapped[list[UserSubscription]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    entitlements: Mapped[list[PremiumEntitlement]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    billing_checkout_sessions: Mapped[list[BillingCheckoutSession]] = relationship(back_populates="plan")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("subscription_plans.id"), index=True)
    plan_code: Mapped[str] = mapped_column(String(80), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    billing_provider: Mapped[str] = mapped_column(String(80), default="manual", index=True)
    external_subscription_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="subscriptions")
    plan: Mapped[SubscriptionPlan] = relationship(back_populates="subscriptions")
    entitlements: Mapped[list[PremiumEntitlement]] = relationship(back_populates="subscription", cascade="all, delete-orphan")
    billing_transactions: Mapped[list[BillingTransaction]] = relationship(back_populates="subscription")


class PremiumEntitlement(Base):
    __tablename__ = "premium_entitlements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    subscription_id: Mapped[str | None] = mapped_column(ForeignKey("user_subscriptions.id"), nullable=True, index=True)
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("subscription_plans.id"), nullable=True, index=True)
    entitlement_key: Mapped[str] = mapped_column(String(120), index=True)
    scope_type: Mapped[str] = mapped_column(String(40), default="global", index=True)
    scope_id: Mapped[str] = mapped_column(String(120), default="*", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    source: Mapped[str] = mapped_column(String(80), default="subscription", index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    usage_limit: Mapped[int] = mapped_column(Integer, default=0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="premium_entitlements")
    subscription: Mapped[UserSubscription | None] = relationship(back_populates="entitlements")
    plan: Mapped[SubscriptionPlan | None] = relationship(back_populates="entitlements")
    access_logs: Mapped[list[PremiumAccessLog]] = relationship(back_populates="entitlement")


class PremiumAccessLog(Base):
    __tablename__ = "premium_access_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    publication_id: Mapped[str | None] = mapped_column(ForeignKey("research_publications.id"), nullable=True, index=True)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("publication_artifacts.id"), nullable=True, index=True)
    snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("publication_snapshots.id"), nullable=True, index=True)
    entitlement_id: Mapped[str | None] = mapped_column(ForeignKey("premium_entitlements.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), default="", index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reason: Mapped[str] = mapped_column(String(220), default="", index=True)
    entitlement_key: Mapped[str] = mapped_column(String(120), default="", index=True)
    artifact_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    ip_address: Mapped[str] = mapped_column(String(80), default="")
    user_agent: Mapped[str] = mapped_column(String(240), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped[User] = relationship(back_populates="premium_access_logs")
    artifact: Mapped[PublicationArtifact | None] = relationship(back_populates="access_logs")
    entitlement: Mapped[PremiumEntitlement | None] = relationship(back_populates="access_logs")


class BillingCheckoutSession(Base):
    __tablename__ = "billing_checkout_sessions"
    __table_args__ = (
        UniqueConstraint("provider", "provider_checkout_id", name="uq_billing_checkout_provider_id"),
        UniqueConstraint("idempotency_key", name="uq_billing_checkout_idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("subscription_plans.id"), index=True)
    plan_code: Mapped[str] = mapped_column(String(80), default="", index=True)
    billing_cycle: Mapped[str] = mapped_column(String(24), default="monthly", index=True)
    provider: Mapped[str] = mapped_column(String(80), default="mock", index=True)
    provider_checkout_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    provider_customer_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    external_reference: Mapped[str] = mapped_column(String(160), default="", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    currency: Mapped[str] = mapped_column(String(8), default="BRL")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    checkout_url: Mapped[str] = mapped_column(Text, default="")
    success_url: Mapped[str] = mapped_column(Text, default="")
    cancel_url: Mapped[str] = mapped_column(Text, default="")
    provider_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="billing_checkout_sessions")
    plan: Mapped[SubscriptionPlan] = relationship(back_populates="billing_checkout_sessions")
    transactions: Mapped[list[BillingTransaction]] = relationship(back_populates="checkout_session", cascade="all, delete-orphan")


class BillingTransaction(Base):
    __tablename__ = "billing_transactions"
    __table_args__ = (
        UniqueConstraint("provider", "provider_payment_id", name="uq_billing_transactions_provider_payment"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    checkout_session_id: Mapped[str | None] = mapped_column(ForeignKey("billing_checkout_sessions.id"), nullable=True, index=True)
    subscription_id: Mapped[str | None] = mapped_column(ForeignKey("user_subscriptions.id"), nullable=True, index=True)
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("subscription_plans.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), default="mock", index=True)
    provider_payment_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    external_reference: Mapped[str] = mapped_column(String(160), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    event_type: Mapped[str] = mapped_column(String(120), default="", index=True)
    currency: Mapped[str] = mapped_column(String(8), default="BRL")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    raw_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped[User] = relationship(back_populates="billing_transactions")
    checkout_session: Mapped[BillingCheckoutSession | None] = relationship(back_populates="transactions")
    subscription: Mapped[UserSubscription | None] = relationship(back_populates="billing_transactions")
    plan: Mapped[SubscriptionPlan | None] = relationship()


class BillingWebhookEvent(Base):
    __tablename__ = "billing_webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_billing_webhook_provider_event"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(80), default="mock", index=True)
    event_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    event_type: Mapped[str] = mapped_column(String(120), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    checkout_session_id: Mapped[str | None] = mapped_column(ForeignKey("billing_checkout_sessions.id"), nullable=True, index=True)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("billing_transactions.id"), nullable=True, index=True)
    raw_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    processing_error: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    checkout_session: Mapped[BillingCheckoutSession | None] = relationship()
    transaction: Mapped[BillingTransaction | None] = relationship()


class DistributionCampaign(Base):
    __tablename__ = "distribution_campaigns"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    publication_id: Mapped[str] = mapped_column(ForeignKey("research_publications.id"), index=True)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("publication_artifacts.id"), nullable=True, index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(220), default="", index=True)
    channel: Mapped[str] = mapped_column(String(40), default="email", index=True)
    audience_type: Mapped[str] = mapped_column(String(80), default="premium_subscribers", index=True)
    provider: Mapped[str] = mapped_column(String(80), default="mock", index=True)
    provider_campaign_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    subject: Mapped[str] = mapped_column(String(220), default="")
    preview_text: Mapped[str] = mapped_column(Text, default="")
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    click_count: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    publication: Mapped[ResearchPublication] = relationship(back_populates="distribution_campaigns")
    artifact: Mapped[PublicationArtifact | None] = relationship(back_populates="distribution_campaigns")
    created_by_user: Mapped[User | None] = relationship()
    recipients: Mapped[list[DistributionRecipient]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    events: Mapped[list[DistributionEventLog]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class DistributionRecipient(Base):
    __tablename__ = "distribution_recipients"
    __table_args__ = (
        UniqueConstraint("campaign_id", "email", name="uq_distribution_recipient_campaign_email"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("distribution_campaigns.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    provider_message_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    entitlement_status: Mapped[str] = mapped_column(String(80), default="", index=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    campaign: Mapped[DistributionCampaign] = relationship(back_populates="recipients")
    user: Mapped[User | None] = relationship(back_populates="distribution_recipients")
    events: Mapped[list[DistributionEventLog]] = relationship(back_populates="recipient", cascade="all, delete-orphan")


class DistributionEventLog(Base):
    __tablename__ = "distribution_event_logs"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_distribution_event_provider_event"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("distribution_campaigns.id"), index=True)
    recipient_id: Mapped[str | None] = mapped_column(ForeignKey("distribution_recipients.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), default="mock", index=True)
    provider_event_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    provider_message_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    event_type: Mapped[str] = mapped_column(String(80), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    campaign: Mapped[DistributionCampaign] = relationship(back_populates="events")
    recipient: Mapped[DistributionRecipient | None] = relationship(back_populates="events")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_preferences_user_key"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(120), index=True)
    value_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="preferences")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    universal_symbol: Mapped[str | None] = mapped_column(String(96), unique=True, index=True, nullable=True)
    ticker: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    asset_class: Mapped[str] = mapped_column(String(40), index=True)
    asset_subclass: Mapped[str] = mapped_column(String(80), default="")
    sector: Mapped[str] = mapped_column(String(120), index=True)
    industry: Mapped[str] = mapped_column(String(120), default="")
    segment: Mapped[str] = mapped_column(String(120), default="")
    currency: Mapped[str] = mapped_column(String(8), default="BRL")
    base_currency: Mapped[str] = mapped_column(String(8), default="")
    trading_currency: Mapped[str] = mapped_column(String(8), default="")
    country_code: Mapped[str] = mapped_column(String(2), default="")
    region: Mapped[str] = mapped_column(String(80), default="")
    market: Mapped[str] = mapped_column(String(80), default="")
    exchange: Mapped[str] = mapped_column(String(80), default="")
    isin: Mapped[str] = mapped_column(String(24), default="")
    cusip: Mapped[str] = mapped_column(String(24), default="")
    provider_symbol: Mapped[str] = mapped_column(String(48), default="")
    last_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transactions: Mapped[list[Transaction]] = relationship(back_populates="asset")
    dividends: Mapped[list[Dividend]] = relationship(back_populates="asset")
    snapshot: Mapped[MarketSnapshot | None] = relationship(back_populates="asset", cascade="all, delete-orphan")
    identifiers: Mapped[list[AssetIdentifier]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    classifications: Mapped[list[AssetClassification]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    exposures: Mapped[list[AssetExposure]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class AssetIdentifier(Base):
    __tablename__ = "asset_identifiers"
    __table_args__ = (
        UniqueConstraint(
            "identifier_type",
            "identifier_value",
            "provider",
            "market",
            name="uq_asset_identifier_scope",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    identifier_type: Mapped[str] = mapped_column(String(40), index=True)
    identifier_value: Mapped[str] = mapped_column(String(120), index=True)
    provider: Mapped[str] = mapped_column(String(80), default="")
    market: Mapped[str] = mapped_column(String(80), default="")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="identifiers")


class AssetClassification(Base):
    __tablename__ = "asset_classifications"
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "taxonomy",
            "level",
            "code",
            name="uq_asset_classification_scope",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    taxonomy: Mapped[str] = mapped_column(String(80), index=True)
    level: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(160))
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=100)
    source: Mapped[str] = mapped_column(String(80), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="classifications")


class AssetExposure(Base):
    __tablename__ = "asset_exposures"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    exposure_type: Mapped[str] = mapped_column(String(40), index=True)
    exposure_key: Mapped[str] = mapped_column(String(120), index=True)
    percentage: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=100)
    source: Mapped[str] = mapped_column(String(80), default="system")
    as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="exposures")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    dividend_yield: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    payout: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    revenue_growth: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    profit_growth: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    net_margin: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    roe: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    roic: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    debt_to_ebitda: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    historical_appreciation: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    dividend_consistency: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    payment_frequency: Mapped[int] = mapped_column(default=0)
    recurring_profit: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    sector_stability: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    pe_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    pvp: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="snapshot")


class MarketDataCacheEntry(Base):
    __tablename__ = "market_data_cache"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    cache_key: Mapped[str] = mapped_column(String(240), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), default="", index=True)
    data_type: Mapped[str] = mapped_column(String(40), default="", index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    quality_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketDataProviderEvent(Base):
    __tablename__ = "market_data_provider_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(24), default="warning", index=True)
    message: Mapped[str] = mapped_column(Text)
    status_code: Mapped[str] = mapped_column(String(24), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class AssetFact(Base):
    __tablename__ = "asset_facts"
    __table_args__ = (
        UniqueConstraint("asset_id", "source", "metric_key", "period", name="uq_asset_fact_latest_scope"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    metric_key: Mapped[str] = mapped_column(String(80), index=True)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    value_text: Mapped[str] = mapped_column(Text, default="")
    currency: Mapped[str] = mapped_column(String(8), default="")
    unit: Mapped[str] = mapped_column(String(32), default="")
    period: Mapped[str] = mapped_column(String(40), default="latest", index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    raw_payload_json: Mapped[str] = mapped_column(Text, default="")
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssetMetricDivergence(Base):
    __tablename__ = "asset_metric_divergences"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    metric_key: Mapped[str] = mapped_column(String(80), index=True)
    primary_source: Mapped[str] = mapped_column(String(80), index=True)
    comparison_source: Mapped[str] = mapped_column(String(80), index=True)
    primary_value: Mapped[Decimal] = mapped_column(Numeric(24, 6), default=0)
    comparison_value: Mapped[Decimal] = mapped_column(Numeric(24, 6), default=0)
    divergence_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    type: Mapped[str] = mapped_column(String(12))
    date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    broker: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="transactions")
    asset: Mapped[Asset] = relationship(back_populates="transactions")


class Dividend(Base):
    __tablename__ = "dividends"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    amount_per_share: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    source: Mapped[str] = mapped_column(String(60), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="dividends")
    asset: Mapped[Asset] = relationship(back_populates="dividends")


class TargetAllocation(Base):
    __tablename__ = "target_allocations"
    __table_args__ = (UniqueConstraint("user_id", "level", "target_key", name="uq_user_target_level_key"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    level: Mapped[str] = mapped_column(String(24))
    target_key: Mapped[str] = mapped_column(String(120))
    percentage: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    profile: Mapped[str] = mapped_column(String(40), default="equilibrado")

    user: Mapped[User] = relationship(back_populates="targets")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(24), default="info")
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(default=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="alerts")
    asset: Mapped[Asset | None] = relationship()


class AlphaEventModel(Base):
    __tablename__ = "alpha_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(24), default="info", index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    status: Mapped[str] = mapped_column(String(32), default="novo", index=True)
    origin: Mapped[str] = mapped_column(String(140), default="alpha_engine", index=True)

    user: Mapped[User] = relationship(back_populates="alpha_events")
    asset: Mapped[Asset | None] = relationship()
