from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Literal


PUBLICATION_STATUSES: tuple[str, ...] = (
    "created",
    "collecting_data",
    "processing",
    "draft",
    "data_pending",
    "in_review",
    "reviewed",
    "approved",
    "published",
    "corrected",
    "archived",
    "cancelled",
)

TERMINAL_PUBLICATION_STATUSES = {"published", "archived", "cancelled"}

PUBLICATION_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "created": ("collecting_data", "cancelled"),
    "collecting_data": ("processing", "data_pending", "cancelled"),
    "processing": ("draft", "data_pending", "cancelled"),
    "data_pending": ("collecting_data", "cancelled"),
    "draft": ("in_review", "data_pending", "cancelled"),
    "in_review": ("reviewed", "draft", "data_pending", "cancelled"),
    "reviewed": ("approved", "draft", "cancelled"),
    "approved": ("published", "draft", "cancelled"),
    "published": ("corrected", "archived"),
    "corrected": ("published", "archived"),
    "archived": (),
    "cancelled": (),
}

PUBLICATION_TYPES: tuple[str, ...] = (
    "monthly_research",
    "extraordinary_update",
    "asset_deep_dive",
    "portfolio_review",
    "market_note",
)

SECTION_STATUSES: tuple[str, ...] = (
    "pending",
    "partial",
    "draft",
    "needs_review",
    "approved",
    "blocked",
)

READINESS_CLASSIFICATIONS: tuple[str, ...] = (
    "blocked",
    "incomplete",
    "ready_for_review",
    "ready_for_approval",
    "ready_for_publication",
)

REVIEW_DECISIONS: tuple[str, ...] = ("approve", "request_changes", "block")
APPROVAL_DECISIONS: tuple[str, ...] = ("approve_publication", "reject_publication")
THESIS_STATUSES: tuple[str, ...] = (
    "draft",
    "active",
    "strengthened",
    "weakened",
    "under_review",
    "archived",
)
THESIS_TYPES: tuple[str, ...] = (
    "recommended_portfolio",
    "fii_model",
    "global_model",
    "crypto_month",
    "asset_deep_dive",
)
RATING_TYPES: tuple[str, ...] = (
    "institutional",
    "income",
    "growth",
    "global",
    "crypto",
)
RATING_LABELS: tuple[str, ...] = (
    "alpha_core",
    "alpha_positive",
    "alpha_neutral",
    "alpha_watch",
    "alpha_restricted",
)
COMMITTEE_DECISIONS: tuple[str, ...] = (
    "approved_for_review",
    "needs_review",
    "request_changes",
    "blocked",
)
COMMITTEE_GATE_STATUSES: tuple[str, ...] = ("pass", "warn", "block")
COMMITTEE_VOTE_DECISIONS: tuple[str, ...] = ("approve", "request_changes", "block")
SNAPSHOT_TYPES: tuple[str, ...] = ("approved_edition", "correction", "archive")
SNAPSHOT_STATUSES: tuple[str, ...] = ("locked", "superseded", "archived")

PublicationStatus = Literal[
    "created",
    "collecting_data",
    "processing",
    "draft",
    "data_pending",
    "in_review",
    "reviewed",
    "approved",
    "published",
    "corrected",
    "archived",
    "cancelled",
]


@dataclass(slots=True)
class PublicationSourceContract:
    sourceType: str
    provider: str
    sourceRef: str
    title: str = ""
    url: str = ""
    observedAt: str = ""
    confidence: float = 0
    status: str = "ok"


@dataclass(slots=True)
class PublicationEvidenceContract:
    evidenceId: str
    domain: str
    fieldName: str
    sourceType: str
    provider: str
    confidence: float
    formulaName: str = ""
    sourceRef: str = ""
    status: str = "ok"


@dataclass(slots=True)
class PublicationSectionContract:
    key: str
    title: str
    order: int
    status: str = "pending"
    confidence: float = 0
    content: str = ""
    dataGaps: list[str] = field(default_factory=list)
    evidenceIds: list[str] = field(default_factory=list)
    requiresHumanApproval: bool = True


@dataclass(slots=True)
class PublicationVersionContract:
    version: str
    status: PublicationStatus
    versionHash: str = ""
    readinessScore: float = 0
    readinessClassification: str = "incomplete"
    sections: list[PublicationSectionContract] = field(default_factory=list)
    sources: list[PublicationSourceContract] = field(default_factory=list)
    evidence: list[PublicationEvidenceContract] = field(default_factory=list)
    changelog: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResearchPublicationContract:
    id: str
    publicationType: str
    period: str
    title: str
    status: PublicationStatus = "created"
    subtitle: str = ""
    referenceDate: str = ""
    closingDate: str = ""
    currentVersion: str = "v0.1"
    confidence: float = 0
    partialDataCount: int = 0
    fallbackCount: int = 0
    legalDisclaimer: str = ""


@dataclass(slots=True)
class PublicationQualityGate:
    id: str
    title: str
    status: str
    severity: str
    reading: str
    evidenceIds: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PublicationReadinessReport:
    publicationId: str
    versionId: str
    score: float
    classification: str
    gates: list[PublicationQualityGate]
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AssetThesisVersionContract:
    thesisId: str
    versionId: str
    version: str
    ticker: str
    thesisStatus: str
    role: str
    thesis: str
    evidenceSummary: str
    riskSummary: str
    monitoringPlan: str
    confidence: float
    conviction: float
    riskLevel: str = ""
    dataQuality: str = ""
    versionHash: str = ""
    evidenceIds: list[str] = field(default_factory=list)
    invalidationTriggers: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AssetThesisContract:
    id: str
    ticker: str
    assetName: str
    assetClass: str
    thesisType: str
    status: str
    currentVersion: str
    confidence: float
    riskLevel: str = ""
    currentVersionId: str = ""
    currentVersionHash: str = ""
    versionCount: int = 0


@dataclass(slots=True)
class AssetRatingVersionContract:
    ratingId: str
    versionId: str
    version: str
    thesisVersionId: str
    ticker: str
    rating: str
    classification: str
    status: str
    scoreFinal: float
    thesisScore: float
    evidenceScore: float
    riskScore: float
    convictionScore: float
    confidenceScore: float
    dataQualityScore: float
    governanceScore: float
    suitabilityScore: float
    summary: str
    riskLevel: str = ""
    dataQuality: str = ""
    versionHash: str = ""
    strengths: list[str] = field(default_factory=list)
    watchpoints: list[str] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)
    evidenceIds: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AssetRatingContract:
    id: str
    ticker: str
    assetName: str
    assetClass: str
    ratingType: str
    status: str
    currentVersion: str
    currentRating: str
    currentClassification: str
    currentScore: float
    confidence: float
    riskLevel: str = ""
    currentVersionId: str = ""
    currentVersionHash: str = ""
    versionCount: int = 0


@dataclass(slots=True)
class CommitteeGateContract:
    id: str
    key: str
    title: str
    status: str
    severity: str
    score: float
    weight: float
    reading: str
    evidenceIds: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CommitteeVoteContract:
    id: str
    voterKey: str
    voterType: str
    decision: str
    confidence: float
    weight: float
    rationale: str
    evidenceIds: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResearchCommitteeRunContract:
    id: str
    publicationId: str
    publicationVersionId: str
    period: str
    committeeType: str
    status: str
    decision: str
    readinessScore: float
    approvalScore: float
    blockerCount: int
    warningCount: int
    gateCount: int
    voteCount: int
    summary: str
    methodologyVersion: str = ""
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    gates: list[CommitteeGateContract] = field(default_factory=list)
    votes: list[CommitteeVoteContract] = field(default_factory=list)


@dataclass(slots=True)
class PublicationSnapshotContract:
    id: str
    publicationId: str
    publicationVersionId: str
    period: str
    snapshotType: str
    status: str
    versionLabel: str
    snapshotHash: str
    contentHash: str
    sourceHash: str
    evidenceHash: str
    approvalHash: str
    isImmutable: bool
    sectionCount: int = 0
    assetCount: int = 0
    sourceCount: int = 0
    evidenceCount: int = 0
    committeeRunId: str = ""
    attributionRunId: str = ""
    reviewId: str = ""
    approvalId: str = ""
    lockedAt: str = ""


@dataclass(slots=True)
class PublicationArtifactContract:
    id: str
    publicationId: str
    publicationVersionId: str
    snapshotId: str
    period: str
    artifactType: str
    status: str
    title: str
    contentType: str
    fileExtension: str
    renderEngine: str
    renderVersion: str
    sourceArtifactId: str
    sourceSnapshotHash: str
    artifactHash: str
    contentSizeBytes: int = 0
    pageCount: int = 0
    hasBinaryContent: bool = False
    createdAt: str = ""


def can_transition_publication(current_status: str, next_status: str) -> bool:
    return next_status in PUBLICATION_STATUS_TRANSITIONS.get(current_status, ())


def is_terminal_publication_status(status: str) -> bool:
    return status in TERMINAL_PUBLICATION_STATUSES


def classify_publication_readiness(score: float, *, has_blocker: bool = False) -> str:
    if has_blocker:
        return "blocked"
    if score >= 92:
        return "ready_for_publication"
    if score >= 82:
        return "ready_for_approval"
    if score >= 68:
        return "ready_for_review"
    if score >= 40:
        return "incomplete"
    return "blocked"


def to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, tuple):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value
