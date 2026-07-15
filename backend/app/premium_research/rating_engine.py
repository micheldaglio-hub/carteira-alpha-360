from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from math import isfinite
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    AssetRating,
    AssetRatingEvidence,
    AssetRatingVersion,
    AssetThesis,
    AssetThesisVersion,
    PublicationVersion,
    ResearchPublication,
)
from app.premium_research.contracts import AssetRatingContract, AssetRatingVersionContract, to_dict
from app.services.data_lineage import record_data_evidence


RATING_ENGINE_VERSION = "2026.07.rating1"
DEFAULT_RATING_TYPE = "institutional"


def sync_ratings_for_publication(
    db: Session,
    *,
    publication: ResearchPublication | None,
    publication_version: PublicationVersion | None,
    user_id: str | None = None,
    rating_type: str = DEFAULT_RATING_TYPE,
    force_new_version: bool = False,
    commit: bool = True,
) -> dict[str, Any]:
    if publication_version is None:
        return _empty_sync_result()
    thesis_versions = db.execute(
        select(AssetThesisVersion)
        .where(AssetThesisVersion.publication_version_id == publication_version.id)
        .order_by(AssetThesisVersion.created_at)
    ).scalars().all()
    return sync_ratings_from_thesis_versions(
        db,
        thesis_versions,
        publication=publication,
        publication_version=publication_version,
        user_id=user_id,
        rating_type=rating_type,
        force_new_version=force_new_version,
        commit=commit,
    )


def sync_ratings_from_thesis_versions(
    db: Session,
    thesis_versions: list[AssetThesisVersion] | tuple[AssetThesisVersion, ...],
    *,
    publication: ResearchPublication | None = None,
    publication_version: PublicationVersion | None = None,
    user_id: str | None = None,
    rating_type: str = DEFAULT_RATING_TYPE,
    force_new_version: bool = False,
    commit: bool = True,
) -> dict[str, Any]:
    created = 0
    unchanged = 0
    ratings = []
    for thesis_version in thesis_versions:
        result = rate_thesis_version(
            db,
            thesis_version,
            publication=publication,
            publication_version=publication_version,
            user_id=user_id,
            rating_type=rating_type,
            force_new_version=force_new_version,
            commit=False,
        )
        ratings.append(result)
        if result.get("createdVersion"):
            created += 1
        else:
            unchanged += 1
    if commit:
        db.commit()
    return {
        "status": "synced",
        "engineVersion": RATING_ENGINE_VERSION,
        "ratingType": rating_type,
        "assetCount": len(thesis_versions),
        "createdVersions": created,
        "unchanged": unchanged,
        "ratings": ratings,
    }


def rate_thesis_version(
    db: Session,
    thesis_version: AssetThesisVersion,
    *,
    publication: ResearchPublication | None = None,
    publication_version: PublicationVersion | None = None,
    user_id: str | None = None,
    rating_type: str = DEFAULT_RATING_TYPE,
    change_reason: str = "Rating gerado a partir de tese versionada.",
    force_new_version: bool = False,
    commit: bool = True,
) -> dict[str, Any]:
    thesis = thesis_version.thesis or db.get(AssetThesis, thesis_version.thesis_id)
    if thesis is None:
        raise ValueError("Rating Engine exige uma tese versionada valida.")

    rating_data = _score_thesis_version(thesis_version)
    rating = _find_or_create_rating(db, thesis, thesis_version, rating_type=rating_type)
    version_hash = _version_hash(thesis_version, rating_data, rating_type=rating_type)

    if rating.current_version_hash == version_hash and not force_new_version:
        if commit:
            db.commit()
        return _rating_result(rating, None, created_version=False)

    previous_version = _latest_version(db, rating.id)
    if previous_version is not None and previous_version.effective_to is None:
        previous_version.effective_to = thesis_version.effective_from or date.today()

    version_label = _next_version_label(db, rating.id)
    rating_version = AssetRatingVersion(
        rating_id=rating.id,
        asset_id=thesis_version.asset_id,
        thesis_id=thesis.id,
        thesis_version_id=thesis_version.id,
        publication_id=publication.id if publication else thesis_version.publication_id,
        publication_version_id=publication_version.id if publication_version else thesis_version.publication_version_id,
        version=version_label,
        version_hash=version_hash,
        rating=rating_data["rating"],
        classification=rating_data["classification"],
        rating_status=rating_data["status"],
        score_final=_decimal(rating_data["scoreFinal"]),
        thesis_score=_decimal(rating_data["components"]["thesis"]),
        evidence_score=_decimal(rating_data["components"]["evidence"]),
        risk_score=_decimal(rating_data["components"]["risk"]),
        conviction_score=_decimal(rating_data["components"]["conviction"]),
        confidence_score=_decimal(rating_data["components"]["confidence"]),
        data_quality_score=_decimal(rating_data["components"]["dataQuality"]),
        governance_score=_decimal(rating_data["components"]["governance"]),
        suitability_score=_decimal(rating_data["components"]["suitability"]),
        risk_level=thesis_version.risk_level,
        data_quality=thesis_version.data_quality,
        summary=rating_data["summary"],
        strengths_json=_json(rating_data["strengths"]),
        watchpoints_json=_json(rating_data["watchpoints"]),
        limits_json=_json(rating_data["limits"]),
        methodology_version=RATING_ENGINE_VERSION,
        source_engine="rating_engine",
        source_thesis_hash=thesis_version.version_hash,
        change_reason=change_reason,
        created_by_user_id=user_id,
        effective_from=thesis_version.effective_from or date.today(),
        metadata_json=_json(
            {
                "engineVersion": RATING_ENGINE_VERSION,
                "ratingType": rating_type,
                "thesisVersion": thesis_version.version,
                "thesisVersionHash": thesis_version.version_hash,
                "weights": _rating_weights(),
            }
        ),
    )
    db.add(rating_version)
    db.flush()

    evidence_links = _persist_rating_evidence(
        db,
        user_id=user_id,
        rating=rating,
        rating_version=rating_version,
        thesis_version=thesis_version,
        rating_data=rating_data,
    )
    rating_version.evidence_ids_json = _json([row.id for row in evidence_links])

    rating.status = _parent_status(rating_data["status"])
    rating.current_version = version_label
    rating.current_version_id = rating_version.id
    rating.current_version_hash = version_hash
    rating.current_rating = rating_data["rating"]
    rating.current_classification = rating_data["classification"]
    rating.current_score = _decimal(rating_data["scoreFinal"])
    rating.confidence = _decimal(rating_data["components"]["confidence"])
    rating.risk_level = thesis_version.risk_level
    rating.source_engine = "rating_engine"
    rating.last_reviewed_at = datetime.now(UTC)
    rating.next_review_at = thesis.next_review_at
    rating.metadata_json = _json(
        {
            "engineVersion": RATING_ENGINE_VERSION,
            "thesisId": thesis.id,
            "thesisVersionId": thesis_version.id,
            "evidenceCount": len(evidence_links),
        }
    )
    rating.updated_at = datetime.now(UTC)
    if commit:
        db.commit()
    return _rating_result(rating, rating_version, created_version=True)


def rating_to_dict(rating: AssetRating, *, include_versions: bool = False) -> dict[str, Any]:
    payload = to_dict(
        AssetRatingContract(
            id=rating.id,
            ticker=rating.ticker,
            assetName=rating.asset_name,
            assetClass=rating.asset_class,
            ratingType=rating.rating_type,
            status=rating.status,
            currentVersion=rating.current_version,
            currentVersionId=rating.current_version_id,
            currentVersionHash=rating.current_version_hash,
            currentRating=rating.current_rating,
            currentClassification=rating.current_classification,
            currentScore=_number(rating.current_score),
            confidence=_number(rating.confidence),
            riskLevel=rating.risk_level,
            versionCount=len(rating.versions),
        )
    )
    if include_versions:
        payload["versions"] = [
            rating_version_to_dict(item)
            for item in sorted(rating.versions, key=lambda row: row.created_at or datetime.min, reverse=True)
        ]
    return payload


def rating_version_to_dict(version: AssetRatingVersion) -> dict[str, Any]:
    parent = version.rating_parent
    return to_dict(
        AssetRatingVersionContract(
            ratingId=version.rating_id,
            versionId=version.id,
            version=version.version,
            thesisVersionId=version.thesis_version_id or "",
            ticker=parent.ticker if parent else "",
            rating=version.rating,
            classification=version.classification,
            status=version.rating_status,
            scoreFinal=_number(version.score_final),
            thesisScore=_number(version.thesis_score),
            evidenceScore=_number(version.evidence_score),
            riskScore=_number(version.risk_score),
            convictionScore=_number(version.conviction_score),
            confidenceScore=_number(version.confidence_score),
            dataQualityScore=_number(version.data_quality_score),
            governanceScore=_number(version.governance_score),
            suitabilityScore=_number(version.suitability_score),
            riskLevel=version.risk_level,
            dataQuality=version.data_quality,
            summary=version.summary,
            versionHash=version.version_hash,
            strengths=_json_load(version.strengths_json, []),
            watchpoints=_json_load(version.watchpoints_json, []),
            limits=_json_load(version.limits_json, []),
            evidenceIds=_json_load(version.evidence_ids_json, []),
        )
    )


def _score_thesis_version(thesis_version: AssetThesisVersion) -> dict[str, Any]:
    components = {
        "thesis": _thesis_score(thesis_version),
        "evidence": _evidence_score(thesis_version),
        "risk": _risk_score(thesis_version.risk_level),
        "conviction": _clamp(_number(thesis_version.conviction)),
        "confidence": _clamp(_number(thesis_version.confidence)),
        "dataQuality": _data_quality_score(thesis_version.data_quality),
        "governance": _governance_score(thesis_version.thesis_status),
        "suitability": _suitability_score(_number(thesis_version.target_weight), thesis_version.role),
    }
    weights = _rating_weights()
    score = sum(components[key] * weight for key, weight in weights.items())
    score = round(_clamp(score), 2)
    rating, classification = _rating_label(score)
    status = _rating_status(score, thesis_version.thesis_status)
    strengths = _strengths(thesis_version, components)
    watchpoints = _watchpoints(thesis_version, components)
    limits = _limits(thesis_version, components)
    summary = _summary(thesis_version, score, rating, classification, components)
    return {
        "scoreFinal": score,
        "rating": rating,
        "classification": classification,
        "status": status,
        "components": components,
        "strengths": strengths,
        "watchpoints": watchpoints,
        "limits": limits,
        "summary": summary,
    }


def _find_or_create_rating(
    db: Session,
    thesis: AssetThesis,
    thesis_version: AssetThesisVersion,
    *,
    rating_type: str,
) -> AssetRating:
    rating = db.execute(
        select(AssetRating).where(
            AssetRating.ticker == thesis.ticker,
            AssetRating.asset_class == thesis.asset_class,
            AssetRating.rating_type == rating_type,
        )
    ).scalar_one_or_none()
    if rating:
        return rating
    rating = AssetRating(
        asset_id=thesis.asset_id or thesis_version.asset_id,
        thesis_id=thesis.id,
        ticker=thesis.ticker,
        asset_name=thesis.asset_name,
        asset_class=thesis.asset_class,
        rating_type=rating_type,
        status="active",
        confidence=thesis.confidence,
        risk_level=thesis.risk_level,
        source_engine="rating_engine",
        next_review_at=thesis.next_review_at,
        metadata_json=_json({"engineVersion": RATING_ENGINE_VERSION}),
    )
    db.add(rating)
    db.flush()
    return rating


def _persist_rating_evidence(
    db: Session,
    *,
    user_id: str | None,
    rating: AssetRating,
    rating_version: AssetRatingVersion,
    thesis_version: AssetThesisVersion,
    rating_data: dict[str, Any],
) -> list[AssetRatingEvidence]:
    specs: list[tuple[str, float, str]] = [
        ("score_final", rating_data["scoreFinal"], "Rating institucional final."),
        ("thesis_score", rating_data["components"]["thesis"], "Completude e clareza da tese versionada."),
        ("evidence_score", rating_data["components"]["evidence"], "Quantidade e qualidade operacional das evidencias ligadas a tese."),
        ("risk_score", rating_data["components"]["risk"], "Penalizacao por risco declarado na tese."),
        ("conviction_score", rating_data["components"]["conviction"], "Conviccao herdada da tese versionada."),
        ("confidence_score", rating_data["components"]["confidence"], "Confianca herdada da tese versionada."),
        ("data_quality_score", rating_data["components"]["dataQuality"], "Qualidade de dados declarada na tese."),
        ("governance_score", rating_data["components"]["governance"], "Status de governanca da tese."),
        ("suitability_score", rating_data["components"]["suitability"], "Adequacao ao papel e peso-alvo do ativo."),
    ]
    rows = []
    for field_name, value, description in specs:
        evidence = record_data_evidence(
            db,
            user_id=user_id,
            asset_id=thesis_version.asset_id,
            domain="rating",
            field_name=field_name,
            value_numeric=value,
            value_text=description,
            unit="score",
            provider="rating_engine",
            source_type="formula",
            source_ref=f"assetRating.{rating.ticker}.{field_name}",
            formula_name=f"rating_engine.{field_name}",
            formula_version=RATING_ENGINE_VERSION,
            input_payload={
                "ratingId": rating.id,
                "ratingVersionId": rating_version.id,
                "thesisId": thesis_version.thesis_id,
                "thesisVersionId": thesis_version.id,
                "thesisVersionHash": thesis_version.version_hash,
                "weights": _rating_weights(),
            },
            confidence=rating_data["components"]["confidence"],
            quality_score=rating_data["components"]["dataQuality"],
            status="ok",
            metadata={"rating": rating_version.rating, "classification": rating_version.classification},
        )
        link = AssetRatingEvidence(
            rating_id=rating.id,
            rating_version_id=rating_version.id,
            evidence_id=evidence.id,
            evidence_key=evidence.evidence_key,
            domain=evidence.domain,
            field_name=evidence.field_name,
            provider=evidence.provider,
            source_type=evidence.source_type,
            confidence=evidence.confidence,
            status=evidence.status,
            metadata_json=_json({"traceId": evidence.trace_id, "sourceRef": evidence.source_ref}),
        )
        db.add(link)
        rows.append(link)
    db.flush()
    return rows


def _rating_result(rating: AssetRating, version: AssetRatingVersion | None, *, created_version: bool) -> dict[str, Any]:
    payload = rating_to_dict(rating, include_versions=False)
    payload["createdVersion"] = created_version
    payload["version"] = rating_version_to_dict(version) if version else None
    return payload


def _latest_version(db: Session, rating_id: str) -> AssetRatingVersion | None:
    return db.execute(
        select(AssetRatingVersion)
        .where(AssetRatingVersion.rating_id == rating_id)
        .order_by(desc(AssetRatingVersion.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _next_version_label(db: Session, rating_id: str) -> str:
    rows = db.execute(select(AssetRatingVersion.version).where(AssetRatingVersion.rating_id == rating_id)).scalars().all()
    numbers = []
    for row in rows:
        try:
            numbers.append(int(str(row).lower().replace("v", "")))
        except Exception:
            continue
    return f"v{(max(numbers) if numbers else 0) + 1}"


def _version_hash(thesis_version: AssetThesisVersion, rating_data: dict[str, Any], *, rating_type: str) -> str:
    payload = {
        "engineVersion": RATING_ENGINE_VERSION,
        "ratingType": rating_type,
        "thesisVersionHash": thesis_version.version_hash,
        "thesisStatus": thesis_version.thesis_status,
        "riskLevel": thesis_version.risk_level,
        "dataQuality": thesis_version.data_quality,
        "components": rating_data["components"],
        "scoreFinal": rating_data["scoreFinal"],
        "rating": rating_data["rating"],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _rating_weights() -> dict[str, float]:
    return {
        "thesis": 0.18,
        "evidence": 0.16,
        "risk": 0.16,
        "conviction": 0.15,
        "confidence": 0.15,
        "dataQuality": 0.10,
        "governance": 0.06,
        "suitability": 0.04,
    }


def _thesis_score(thesis_version: AssetThesisVersion) -> float:
    score = 25.0
    if len(thesis_version.thesis_text or "") >= 80:
        score += 25
    elif thesis_version.thesis_text:
        score += 15
    if thesis_version.evidence_summary:
        score += 20
    if thesis_version.risk_summary:
        score += 15
    if thesis_version.monitoring_plan:
        score += 15
    return _clamp(score)


def _evidence_score(thesis_version: AssetThesisVersion) -> float:
    link_count = len(thesis_version.evidence_links or [])
    declared = len(_json_load(thesis_version.evidence_ids_json, []))
    summary_bonus = 20 if thesis_version.evidence_summary else 0
    return _clamp(35 + min(45, max(link_count, declared) * 8) + summary_bonus)


def _risk_score(risk_level: str) -> float:
    normalized = str(risk_level or "").lower().replace(" ", "_").replace("-", "_")
    table = {
        "baixissimo": 96,
        "baixo": 92,
        "baixo_moderado": 84,
        "moderado": 74,
        "moderado_arrojado": 64,
        "arrojado": 58,
        "alto": 45,
        "alto_risco": 40,
        "altissimo": 30,
        "extremo": 22,
    }
    return float(table.get(normalized, 68))


def _data_quality_score(data_quality: str) -> float:
    normalized = str(data_quality or "").lower().replace(" ", "_").replace("-", "_")
    if normalized in {"completo", "completos", "complete", "high"}:
        return 92
    if normalized in {"analisado", "ok", "boa", "good"}:
        return 82
    if normalized in {"parcial", "parciais", "partial"}:
        return 58
    if normalized in {"fallback", "low_confidence"}:
        return 36
    if normalized in {"insuficiente", "insufficient"}:
        return 25
    return 72


def _governance_score(thesis_status: str) -> float:
    normalized = str(thesis_status or "").lower()
    table = {
        "strengthened": 94,
        "active": 86,
        "draft": 62,
        "under_review": 54,
        "weakened": 42,
        "archived": 20,
    }
    return float(table.get(normalized, 70))


def _suitability_score(target_weight: float, role: str) -> float:
    role_bonus = 8 if str(role or "").strip() else 0
    if target_weight <= 0:
        return 50 + role_bonus
    if target_weight <= 5:
        return 72 + role_bonus
    if target_weight <= 15:
        return 88 + role_bonus
    if target_weight <= 25:
        return 78 + role_bonus
    return 58 + role_bonus


def _rating_label(score: float) -> tuple[str, str]:
    if score >= 85:
        return "alpha_core", "Nucleo Alpha"
    if score >= 75:
        return "alpha_positive", "Forte para acompanhamento"
    if score >= 62:
        return "alpha_neutral", "Neutro qualificado"
    if score >= 50:
        return "alpha_watch", "Em observacao"
    return "alpha_restricted", "Fora dos criterios atuais"


def _rating_status(score: float, thesis_status: str) -> str:
    if thesis_status in {"weakened", "under_review"}:
        return "needs_review"
    if score < 50:
        return "restricted"
    if score < 62:
        return "needs_review"
    return "active"


def _parent_status(status: str) -> str:
    if status == "restricted":
        return "restricted"
    if status == "needs_review":
        return "under_review"
    return "active"


def _strengths(thesis_version: AssetThesisVersion, components: dict[str, float]) -> list[str]:
    items = []
    if components["conviction"] >= 80:
        items.append("Conviccao analitica elevada na tese versionada.")
    if components["confidence"] >= 80:
        items.append("Confianca dos dados em faixa forte para esta leitura.")
    if components["risk"] >= 80:
        items.append("Nivel de risco declarado compativel com carteira institucional.")
    if thesis_version.evidence_summary:
        items.append("Tese possui evidencias registradas para auditoria.")
    return items or ["Tese possui estrutura minima para acompanhamento institucional."]


def _watchpoints(thesis_version: AssetThesisVersion, components: dict[str, float]) -> list[str]:
    items = []
    if components["dataQuality"] < 70:
        items.append("Qualidade dos dados ainda limita a confianca do rating.")
    if components["risk"] < 65:
        items.append("Risco declarado exige acompanhamento mais proximo.")
    if thesis_version.thesis_status in {"under_review", "weakened"}:
        items.append("Tese esta em revisao e nao deve elevar conviccao automaticamente.")
    if not thesis_version.risk_summary:
        items.append("Resumo de riscos precisa ser enriquecido no proximo ciclo.")
    return items


def _limits(thesis_version: AssetThesisVersion, components: dict[str, float]) -> list[str]:
    limits = [
        "Rating analitico nao e ordem de compra ou venda.",
        "Rating depende da qualidade da tese versionada e das evidencias disponiveis.",
    ]
    if components["evidence"] < 70:
        limits.append("Cobertura de evidencias ainda pode ser expandida antes de publicacao premium.")
    if not thesis_version.monitoring_plan:
        limits.append("Plano de monitoramento precisa ser formalizado.")
    return limits


def _summary(
    thesis_version: AssetThesisVersion,
    score: float,
    rating: str,
    classification: str,
    components: dict[str, float],
) -> str:
    ticker = thesis_version.thesis.ticker if thesis_version.thesis else "ativo"
    return (
        f"{ticker} recebeu rating {rating} ({classification}) com score {score:.2f}/100. "
        f"A leitura usa a tese versionada {thesis_version.version}, score de tese {components['thesis']:.2f}, "
        f"evidencias {components['evidence']:.2f}, risco {components['risk']:.2f} e confianca {components['confidence']:.2f}. "
        "Este rating organiza a leitura institucional e nao representa ordem automatica de compra ou venda."
    )


def _empty_sync_result() -> dict[str, Any]:
    return {
        "status": "synced",
        "engineVersion": RATING_ENGINE_VERSION,
        "ratingType": DEFAULT_RATING_TYPE,
        "assetCount": 0,
        "createdVersions": 0,
        "unchanged": 0,
        "ratings": [],
    }


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


def _clamp(value: float, lower: float = 0, upper: float = 100) -> float:
    return round(max(lower, min(upper, value)), 2)
