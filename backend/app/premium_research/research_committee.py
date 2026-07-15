from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from math import isfinite
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    AssetRatingVersion,
    AssetThesisVersion,
    DataEvidenceLedger,
    PublicationVersion,
    ResearchCommitteeGateResult,
    ResearchCommitteeRun,
    ResearchCommitteeVote,
    ResearchPublication,
)
from app.premium_research.contracts import (
    CommitteeGateContract,
    CommitteeVoteContract,
    ResearchCommitteeRunContract,
    to_dict,
)
from app.services.data_lineage import record_data_evidence


RESEARCH_COMMITTEE_VERSION = "2026.07.committee1"
DEFAULT_COMMITTEE_TYPE = "premium_research"


@dataclass(slots=True)
class _Gate:
    key: str
    title: str
    status: str
    severity: str
    score: float
    weight: float
    reading: str
    evidence_ids: list[str]
    metadata: dict[str, Any]


@dataclass(slots=True)
class _Vote:
    voter_key: str
    voter_type: str
    decision: str
    confidence: float
    weight: float
    rationale: str
    evidence_ids: list[str]
    metadata: dict[str, Any]


def run_research_committee_for_publication(
    db: Session,
    *,
    publication: ResearchPublication | None,
    publication_version: PublicationVersion | None,
    user_id: str | None = None,
    committee_type: str = DEFAULT_COMMITTEE_TYPE,
    commit: bool = True,
) -> dict[str, Any]:
    """Run institutional gates for the latest premium research draft.

    This is intentionally not an approval/publishing command. The committee
    produces an auditable decision that decides whether the draft can move to
    human review, needs changes, or is blocked.
    """

    if publication_version is None and publication is not None:
        publication_version = _latest_publication_version(db, publication.id)
    return run_research_committee(
        db,
        publication=publication,
        publication_version=publication_version,
        user_id=user_id,
        committee_type=committee_type,
        commit=commit,
    )


def run_research_committee(
    db: Session,
    *,
    publication: ResearchPublication | None = None,
    publication_version: PublicationVersion | None = None,
    thesis_versions: list[AssetThesisVersion] | tuple[AssetThesisVersion, ...] | None = None,
    rating_versions: list[AssetRatingVersion] | tuple[AssetRatingVersion, ...] | None = None,
    user_id: str | None = None,
    committee_type: str = DEFAULT_COMMITTEE_TYPE,
    commit: bool = True,
) -> dict[str, Any]:
    theses = list(thesis_versions or _fetch_thesis_versions(db, publication_version))
    ratings = list(rating_versions or _fetch_rating_versions(db, publication_version, theses))
    evidence = _collect_evidence(theses, ratings, publication_version)
    gates = _build_gates(publication, publication_version, theses, ratings, evidence)
    votes = _build_votes(gates)
    blockers = _blockers(gates, votes)
    warnings = _warnings(gates, votes)
    approval_score = _approval_score(gates)
    readiness_score = _readiness_score(approval_score, blockers, warnings)
    decision = _decision(gates, votes, approval_score)
    summary = _summary(decision, approval_score, theses, ratings, blockers, warnings)

    run = ResearchCommitteeRun(
        publication_id=publication.id if publication else None,
        publication_version_id=publication_version.id if publication_version else None,
        period=publication.period if publication else "",
        committee_type=committee_type,
        status="completed",
        decision=decision,
        readiness_score=_decimal(readiness_score),
        approval_score=_decimal(approval_score),
        blocker_count=len(blockers),
        warning_count=len(warnings),
        gate_count=len(gates),
        vote_count=len(votes),
        source_engine="research_committee",
        methodology_version=RESEARCH_COMMITTEE_VERSION,
        summary=summary,
        blockers_json=_json(blockers),
        warnings_json=_json(warnings),
        created_by_user_id=user_id,
        metadata_json=_json(
            {
                "engineVersion": RESEARCH_COMMITTEE_VERSION,
                "thesisVersionCount": len(theses),
                "ratingVersionCount": len(ratings),
                "evidenceCount": len(evidence),
                "decisionPolicy": "blockers override warnings; warnings can request changes; no automatic publishing",
            }
        ),
        updated_at=datetime.now(UTC),
    )
    db.add(run)
    db.flush()

    gate_rows = [_persist_gate(db, run, gate) for gate in gates]
    vote_rows = [_persist_vote(db, run, vote) for vote in votes]
    committee_evidence = _record_committee_evidence(
        db,
        user_id=user_id,
        run=run,
        approval_score=approval_score,
        decision=decision,
        gates=gates,
        votes=votes,
    )
    run.metadata_json = _json(
        _json_load(run.metadata_json, {})
        | {
            "committeeEvidenceId": committee_evidence.id,
            "gateIds": [row.id for row in gate_rows],
            "voteIds": [row.id for row in vote_rows],
        }
    )
    if commit:
        db.commit()
    return committee_run_to_dict(run)


def committee_run_to_dict(run: ResearchCommitteeRun, *, include_details: bool = True) -> dict[str, Any]:
    gates = []
    votes = []
    if include_details:
        gates = [
            CommitteeGateContract(
                id=row.id,
                key=row.gate_key,
                title=row.title,
                status=row.status,
                severity=row.severity,
                score=_number(row.score),
                weight=_number(row.weight),
                reading=row.reading,
                evidenceIds=_json_load(row.evidence_ids_json, []),
            )
            for row in sorted(run.gate_results, key=lambda item: item.created_at or datetime.min)
        ]
        votes = [
            CommitteeVoteContract(
                id=row.id,
                voterKey=row.voter_key,
                voterType=row.voter_type,
                decision=row.decision,
                confidence=_number(row.confidence),
                weight=_number(row.weight),
                rationale=row.rationale,
                evidenceIds=_json_load(row.evidence_ids_json, []),
            )
            for row in sorted(run.votes, key=lambda item: item.created_at or datetime.min)
        ]
    return to_dict(
        ResearchCommitteeRunContract(
            id=run.id,
            publicationId=run.publication_id or "",
            publicationVersionId=run.publication_version_id or "",
            period=run.period,
            committeeType=run.committee_type,
            status=run.status,
            decision=run.decision,
            readinessScore=_number(run.readiness_score),
            approvalScore=_number(run.approval_score),
            blockerCount=run.blocker_count,
            warningCount=run.warning_count,
            gateCount=run.gate_count,
            voteCount=run.vote_count,
            methodologyVersion=run.methodology_version,
            summary=run.summary,
            blockers=_json_load(run.blockers_json, []),
            warnings=_json_load(run.warnings_json, []),
            gates=gates,
            votes=votes,
        )
    )


def _latest_publication_version(db: Session, publication_id: str) -> PublicationVersion | None:
    return db.execute(
        select(PublicationVersion)
        .where(PublicationVersion.publication_id == publication_id)
        .order_by(desc(PublicationVersion.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _fetch_thesis_versions(db: Session, publication_version: PublicationVersion | None) -> list[AssetThesisVersion]:
    if publication_version is None:
        return []
    return list(
        db.execute(
            select(AssetThesisVersion)
            .where(AssetThesisVersion.publication_version_id == publication_version.id)
            .order_by(AssetThesisVersion.created_at)
        )
        .scalars()
        .all()
    )


def _fetch_rating_versions(
    db: Session,
    publication_version: PublicationVersion | None,
    thesis_versions: list[AssetThesisVersion],
) -> list[AssetRatingVersion]:
    if publication_version is not None:
        return list(
            db.execute(
                select(AssetRatingVersion)
                .where(AssetRatingVersion.publication_version_id == publication_version.id)
                .order_by(AssetRatingVersion.created_at)
            )
            .scalars()
            .all()
        )
    thesis_ids = [item.id for item in thesis_versions]
    if not thesis_ids:
        return []
    return list(
        db.execute(
            select(AssetRatingVersion)
            .where(AssetRatingVersion.thesis_version_id.in_(thesis_ids))
            .order_by(AssetRatingVersion.created_at)
        )
        .scalars()
        .all()
    )


def _collect_evidence(
    theses: list[AssetThesisVersion],
    ratings: list[AssetRatingVersion],
    publication_version: PublicationVersion | None,
) -> list[Any]:
    rows: list[Any] = []
    for thesis in theses:
        rows.extend(thesis.evidence_links or [])
    for rating in ratings:
        rows.extend(rating.evidence_links or [])
    if publication_version is not None:
        rows.extend(publication_version.publication.evidence_links if publication_version.publication else [])
    return rows


def _build_gates(
    publication: ResearchPublication | None,
    publication_version: PublicationVersion | None,
    theses: list[AssetThesisVersion],
    ratings: list[AssetRatingVersion],
    evidence: list[Any],
) -> list[_Gate]:
    thesis_count = len(theses)
    rating_count = len(ratings)
    evidence_ids = _evidence_ids(evidence)
    evidence_confidence = _avg([_number(getattr(item, "confidence", 0)) for item in evidence])
    avg_data_quality = _avg([_number(item.data_quality_score) for item in ratings])
    avg_rating_score = _avg([_number(item.score_final) for item in ratings])
    restricted = [item for item in ratings if item.rating_status == "restricted" or item.rating == "alpha_restricted"]
    needs_review = [item for item in ratings if item.rating_status == "needs_review" or item.rating == "alpha_watch"]
    high_risk = [item for item in ratings if _risk_level_blocker(item.risk_level)]
    version_score = _number(publication_version.readiness_score) if publication_version else 0
    legal_disclaimer = str(publication.legal_disclaimer or "") if publication else ""

    gates = [
        _gate(
            key="thesis_coverage",
            title="Cobertura de teses versionadas",
            value=100 if thesis_count else 0,
            status="pass" if thesis_count else "block",
            severity="critical",
            reading=(
                f"{thesis_count} tese(s) versionada(s) foram encontradas para a publicacao."
                if thesis_count
                else "Nenhuma tese versionada foi encontrada. A publicacao premium fica bloqueada."
            ),
            weight=18,
            evidence_ids=evidence_ids,
            metadata={"thesisVersionCount": thesis_count},
        ),
        _gate(
            key="rating_coverage",
            title="Rating calculado sobre tese historica",
            value=_coverage_score(rating_count, thesis_count),
            status=_coverage_status(rating_count, thesis_count),
            severity="critical",
            reading=(
                f"{rating_count} rating(s) foram calculados para {thesis_count} tese(s)."
                if thesis_count
                else "Sem tese, nao ha rating institucional confiavel."
            ),
            weight=18,
            evidence_ids=evidence_ids,
            metadata={"ratingVersionCount": rating_count, "thesisVersionCount": thesis_count},
        ),
        _gate(
            key="evidence_ledger",
            title="Evidence Ledger e rastreabilidade",
            value=evidence_confidence if evidence_ids else 0,
            status="block" if not evidence_ids else ("warn" if evidence_confidence < 70 else "pass"),
            severity="critical",
            reading=(
                f"{len(evidence_ids)} evidencia(s) ligadas; confianca media {evidence_confidence:.0f}/100."
                if evidence_ids
                else "Nenhuma evidencia auditavel foi ligada ao comite."
            ),
            weight=16,
            evidence_ids=evidence_ids,
            metadata={"evidenceCount": len(evidence_ids), "averageEvidenceConfidence": evidence_confidence},
        ),
        _gate(
            key="data_confidence",
            title="Confianca dos dados",
            value=avg_data_quality,
            status="block" if avg_data_quality and avg_data_quality < 50 else ("warn" if avg_data_quality < 70 else "pass"),
            severity="high",
            reading=(
                f"Qualidade media dos dados dos ratings: {avg_data_quality:.0f}/100."
                if ratings
                else "Sem ratings, a qualidade de dados nao pode ser validada."
            ),
            weight=14,
            evidence_ids=evidence_ids,
            metadata={"averageDataQualityScore": avg_data_quality},
        ),
        _gate(
            key="guardian_risk",
            title="Guardian e risco de publicacao",
            value=_guardian_score(ratings, restricted, needs_review, high_risk),
            status="block" if restricted or high_risk else ("warn" if needs_review else "pass"),
            severity="high",
            reading=_guardian_reading(restricted, needs_review, high_risk),
            weight=14,
            evidence_ids=evidence_ids,
            metadata={
                "restrictedCount": len(restricted),
                "needsReviewCount": len(needs_review),
                "highRiskCount": len(high_risk),
                "averageRatingScore": avg_rating_score,
            },
        ),
        _gate(
            key="publication_readiness",
            title="Readiness editorial",
            value=version_score,
            status="block" if publication_version and version_score < 40 else ("warn" if version_score < 68 else "pass"),
            severity="medium",
            reading=(
                f"Readiness editorial da versao: {version_score:.0f}/100."
                if publication_version
                else "Sem versao editorial associada; comite roda apenas como avaliacao tecnica."
            ),
            weight=10,
            evidence_ids=evidence_ids,
            metadata={"publicationReadinessScore": version_score},
        ),
        _gate(
            key="legal_safety",
            title="Aviso legal e seguranca editorial",
            value=100 if legal_disclaimer else (70 if publication is None else 30),
            status="pass" if legal_disclaimer or publication is None else "warn",
            severity="medium",
            reading=(
                "Aviso legal da publicacao esta presente e exige revisao/aprovacao humana."
                if legal_disclaimer
                else "Comite sem publicacao associada ou aviso legal pendente."
            ),
            weight=10,
            evidence_ids=evidence_ids,
            metadata={"hasLegalDisclaimer": bool(legal_disclaimer), "hasPublication": publication is not None},
        ),
    ]
    return gates


def _build_votes(gates: list[_Gate]) -> list[_Vote]:
    by_key = {gate.key: gate for gate in gates}
    return [
        _vote_from_gates(
            "thesis_engine",
            "engine",
            [by_key["thesis_coverage"]],
            "A tese historica precisa existir e estar versionada antes de virar publicacao premium.",
            20,
        ),
        _vote_from_gates(
            "rating_engine",
            "engine",
            [by_key["rating_coverage"], by_key["guardian_risk"]],
            "O rating deve estar calculado sobre tese versionada e sem bloqueio de risco.",
            20,
        ),
        _vote_from_gates(
            "data_confidence",
            "engine",
            [by_key["data_confidence"]],
            "A qualidade dos dados precisa sustentar a leitura institucional.",
            18,
        ),
        _vote_from_gates(
            "guardian",
            "engine",
            [by_key["guardian_risk"], by_key["legal_safety"]],
            "Risco, linguagem e governanca nao podem permitir publicacao automatica inadequada.",
            22,
        ),
        _vote_from_gates(
            "evidence_ledger",
            "ledger",
            [by_key["evidence_ledger"], by_key["publication_readiness"]],
            "A decisao precisa ter evidencias rastreaveis e readiness editorial minimo.",
            20,
        ),
    ]


def _vote_from_gates(voter_key: str, voter_type: str, gates: list[_Gate], rationale: str, weight: float) -> _Vote:
    if any(gate.status == "block" for gate in gates):
        decision = "block"
    elif any(gate.status == "warn" for gate in gates):
        decision = "request_changes"
    else:
        decision = "approve"
    confidence = _avg([gate.score for gate in gates])
    evidence_ids = sorted({evidence_id for gate in gates for evidence_id in gate.evidence_ids})
    return _Vote(
        voter_key=voter_key,
        voter_type=voter_type,
        decision=decision,
        confidence=confidence,
        weight=weight,
        rationale=rationale,
        evidence_ids=evidence_ids,
        metadata={"gateKeys": [gate.key for gate in gates]},
    )


def _gate(
    *,
    key: str,
    title: str,
    value: float,
    status: str,
    severity: str,
    reading: str,
    weight: float,
    evidence_ids: list[str],
    metadata: dict[str, Any],
) -> _Gate:
    return _Gate(
        key=key,
        title=title,
        status=status,
        severity=severity,
        score=round(max(0, min(100, value)), 2),
        weight=weight,
        reading=reading,
        evidence_ids=evidence_ids,
        metadata=metadata,
    )


def _coverage_score(rating_count: int, thesis_count: int) -> float:
    if thesis_count <= 0:
        return 0
    return round(min(100, (rating_count / thesis_count) * 100), 2)


def _coverage_status(rating_count: int, thesis_count: int) -> str:
    if thesis_count <= 0 or rating_count <= 0:
        return "block"
    if rating_count < thesis_count:
        return "warn"
    return "pass"


def _guardian_score(
    ratings: list[AssetRatingVersion],
    restricted: list[AssetRatingVersion],
    needs_review: list[AssetRatingVersion],
    high_risk: list[AssetRatingVersion],
) -> float:
    if not ratings:
        return 0
    score = _avg([_number(item.score_final) for item in ratings])
    score -= len(restricted) * 18
    score -= len(high_risk) * 15
    score -= len(needs_review) * 8
    return round(max(0, min(100, score)), 2)


def _guardian_reading(
    restricted: list[AssetRatingVersion],
    needs_review: list[AssetRatingVersion],
    high_risk: list[AssetRatingVersion],
) -> str:
    if restricted or high_risk:
        tickers = sorted({item.rating_parent.ticker if item.rating_parent else "" for item in restricted + high_risk if item})
        return f"Guardian bloqueou a publicacao: {len(restricted)} rating(s) restrito(s) e {len(high_risk)} risco(s) alto(s). Ativos: {', '.join(tickers) or 'nao informado'}."
    if needs_review:
        tickers = sorted({item.rating_parent.ticker if item.rating_parent else "" for item in needs_review if item})
        return f"Guardian pede revisao: {len(needs_review)} ativo(s) em observacao ({', '.join(tickers) or 'nao informado'})."
    return "Guardian nao encontrou bloqueio de risco para a publicacao premium."


def _risk_level_blocker(risk_level: str) -> bool:
    normalized = str(risk_level or "").lower().replace(" ", "_").replace("-", "_")
    return normalized in {"alto", "alto_risco", "altissimo", "extremo"}


def _approval_score(gates: list[_Gate]) -> float:
    total_weight = sum(gate.weight for gate in gates) or 1
    weighted = sum(gate.score * gate.weight for gate in gates) / total_weight
    block_penalty = sum(18 for gate in gates if gate.status == "block")
    warn_penalty = sum(4 for gate in gates if gate.status == "warn")
    return round(max(0, min(100, weighted - block_penalty - warn_penalty)), 2)


def _readiness_score(approval_score: float, blockers: list[str], warnings: list[str]) -> float:
    if blockers:
        return min(49, approval_score)
    if len(warnings) >= 3:
        return min(72, approval_score)
    return approval_score


def _decision(gates: list[_Gate], votes: list[_Vote], approval_score: float) -> str:
    if any(gate.status == "block" for gate in gates) or any(vote.decision == "block" for vote in votes):
        return "blocked"
    request_count = sum(1 for vote in votes if vote.decision == "request_changes")
    warn_count = sum(1 for gate in gates if gate.status == "warn")
    if approval_score < 68 or request_count >= 2:
        return "request_changes"
    if warn_count or request_count:
        return "needs_review"
    return "approved_for_review"


def _blockers(gates: list[_Gate], votes: list[_Vote]) -> list[str]:
    items = [gate.reading for gate in gates if gate.status == "block"]
    items.extend(vote.rationale for vote in votes if vote.decision == "block")
    return list(dict.fromkeys(items))


def _warnings(gates: list[_Gate], votes: list[_Vote]) -> list[str]:
    items = [gate.reading for gate in gates if gate.status == "warn"]
    items.extend(vote.rationale for vote in votes if vote.decision == "request_changes")
    return list(dict.fromkeys(items))


def _summary(
    decision: str,
    approval_score: float,
    theses: list[AssetThesisVersion],
    ratings: list[AssetRatingVersion],
    blockers: list[str],
    warnings: list[str],
) -> str:
    decision_text = {
        "approved_for_review": "liberou a edicao para revisao humana",
        "needs_review": "pediu revisao humana com pontos de acompanhamento",
        "request_changes": "solicitou ajustes antes da revisao final",
        "blocked": "bloqueou a publicacao premium",
    }.get(decision, "gerou decisao tecnica")
    detail = "sem bloqueios" if not blockers else f"{len(blockers)} bloqueio(s)"
    if not blockers and warnings:
        detail = f"{len(warnings)} aviso(s)"
    return (
        f"O Research Committee {decision_text} com score {approval_score:.0f}/100, "
        f"avaliando {len(theses)} tese(s), {len(ratings)} rating(s) e {detail}. "
        "A decisao e uma etapa de governanca e nao publica o relatorio automaticamente."
    )


def _persist_gate(db: Session, run: ResearchCommitteeRun, gate: _Gate) -> ResearchCommitteeGateResult:
    row = ResearchCommitteeGateResult(
        run_id=run.id,
        gate_key=gate.key,
        title=gate.title,
        status=gate.status,
        severity=gate.severity,
        score=_decimal(gate.score),
        weight=_decimal(gate.weight),
        reading=gate.reading,
        evidence_ids_json=_json(gate.evidence_ids),
        metadata_json=_json(gate.metadata),
    )
    db.add(row)
    db.flush()
    return row


def _persist_vote(db: Session, run: ResearchCommitteeRun, vote: _Vote) -> ResearchCommitteeVote:
    row = ResearchCommitteeVote(
        run_id=run.id,
        voter_key=vote.voter_key,
        voter_type=vote.voter_type,
        decision=vote.decision,
        confidence=_decimal(vote.confidence),
        weight=_decimal(vote.weight),
        rationale=vote.rationale,
        evidence_ids_json=_json(vote.evidence_ids),
        metadata_json=_json(vote.metadata),
    )
    db.add(row)
    db.flush()
    return row


def _record_committee_evidence(
    db: Session,
    *,
    user_id: str | None,
    run: ResearchCommitteeRun,
    approval_score: float,
    decision: str,
    gates: list[_Gate],
    votes: list[_Vote],
) -> DataEvidenceLedger:
    return record_data_evidence(
        db,
        user_id=user_id,
        domain="research_committee",
        field_name="approval_score",
        value_numeric=approval_score,
        value_text=run.summary,
        unit="score",
        provider="research_committee",
        source_type="formula",
        source_ref=f"researchCommittee.{run.id}.decision",
        formula_name="research_committee.approval_score",
        formula_version=RESEARCH_COMMITTEE_VERSION,
        input_payload={
            "runId": run.id,
            "publicationId": run.publication_id,
            "publicationVersionId": run.publication_version_id,
            "decision": decision,
            "gates": [{"key": gate.key, "status": gate.status, "score": gate.score, "weight": gate.weight} for gate in gates],
            "votes": [{"voter": vote.voter_key, "decision": vote.decision, "confidence": vote.confidence} for vote in votes],
        },
        confidence=approval_score,
        quality_score=approval_score,
        status="ok" if decision in {"approved_for_review", "needs_review"} else "needs_review",
        metadata={"runId": run.id, "decision": decision, "methodologyVersion": RESEARCH_COMMITTEE_VERSION},
    )


def _evidence_ids(rows: list[Any]) -> list[str]:
    ids: list[str] = []
    for row in rows:
        row_id = getattr(row, "evidence_id", None) or getattr(row, "id", None)
        if row_id:
            ids.append(str(row_id))
    return sorted(dict.fromkeys(ids))


def _avg(values: list[float]) -> float:
    clean = [value for value in values if isfinite(value)]
    if not clean:
        return 0.0
    return round(sum(clean) / len(clean), 2)


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
        if isfinite(number):
            return number
    except Exception:
        return 0.0
    return 0.0


def _decimal(value: Any) -> Decimal:
    return Decimal(str(round(_number(value), 6)))
