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
    Asset,
    AssetThesis,
    AssetThesisEvidence,
    AssetThesisVersion,
    DataEvidenceLedger,
    PublicationVersion,
    ResearchPublication,
)
from app.premium_research.contracts import AssetThesisContract, AssetThesisVersionContract, to_dict
from app.services.data_lineage import record_data_evidence


THESIS_ENGINE_VERSION = "2026.07.thesis1"
DEFAULT_THESIS_TYPE = "recommended_portfolio"
DEFAULT_INVALIDATION_TRIGGERS = [
    "Deterioracao relevante de fundamentos.",
    "Corte estrutural de proventos ou piora de geracao de caixa.",
    "Aumento material de risco, divida, governanca ou regulacao.",
    "Queda relevante de confianca dos dados usados na tese.",
]


def sync_theses_from_recommended_report(
    db: Session,
    report: dict[str, Any],
    *,
    publication: ResearchPublication | None = None,
    publication_version: PublicationVersion | None = None,
    user_id: str | None = None,
    thesis_type: str = DEFAULT_THESIS_TYPE,
    force_new_version: bool = False,
    commit: bool = True,
) -> dict[str, Any]:
    asset_reports = report.get("assetReports") or []
    created = 0
    unchanged = 0
    versions = []
    for asset_report in asset_reports:
        result = upsert_asset_thesis(
            db,
            asset_report,
            publication=publication,
            publication_version=publication_version,
            user_id=user_id,
            thesis_type=thesis_type,
            source_report_id=str(report.get("id") or ""),
            source_engine="recommended_portfolio_engine",
            force_new_version=force_new_version,
            commit=False,
        )
        versions.append(result)
        if result.get("createdVersion"):
            created += 1
        else:
            unchanged += 1
    if commit:
        db.commit()
    return {
        "status": "synced",
        "engineVersion": THESIS_ENGINE_VERSION,
        "reportId": report.get("id"),
        "assetCount": len(asset_reports),
        "createdVersions": created,
        "unchanged": unchanged,
        "versions": versions,
    }


def upsert_asset_thesis(
    db: Session,
    asset_report: dict[str, Any],
    *,
    publication: ResearchPublication | None = None,
    publication_version: PublicationVersion | None = None,
    user_id: str | None = None,
    thesis_type: str = DEFAULT_THESIS_TYPE,
    source_report_id: str = "",
    source_engine: str = "recommended_portfolio_engine",
    change_reason: str = "Ciclo editorial mensal.",
    force_new_version: bool = False,
    commit: bool = True,
) -> dict[str, Any]:
    normalized = _normalize_asset_report(db, asset_report, thesis_type=thesis_type)
    thesis = _find_or_create_thesis(db, normalized, source_engine=source_engine)
    version_hash = _version_hash(normalized, source_report_id=source_report_id, source_engine=source_engine)
    if thesis.current_version_hash == version_hash and not force_new_version:
        if commit:
            db.commit()
        return _thesis_result(thesis, None, created_version=False)

    previous_version = _latest_version(db, thesis.id)
    if previous_version is not None and previous_version.effective_to is None:
        previous_version.effective_to = normalized["effective_from"]

    version_label = _next_version_label(db, thesis.id)
    thesis_version = AssetThesisVersion(
        thesis_id=thesis.id,
        asset_id=normalized["asset_id"],
        publication_id=publication.id if publication else None,
        publication_version_id=publication_version.id if publication_version else None,
        version=version_label,
        version_hash=version_hash,
        thesis_status=normalized["thesis_status"],
        role=normalized["role"],
        thesis_text=normalized["thesis_text"],
        evidence_summary=normalized["evidence_summary"],
        risk_summary=normalized["risk_summary"],
        monitoring_plan=normalized["monitoring_plan"],
        invalidation_triggers_json=_json(normalized["invalidation_triggers"]),
        evidence_ids_json=_json(normalized["evidence_items"]),
        source_report_id=source_report_id,
        source_engine=source_engine,
        confidence=_decimal(normalized["confidence"]),
        conviction=_decimal(normalized["conviction"]),
        target_weight=_decimal(normalized["target_weight"]),
        risk_level=normalized["risk_level"],
        data_quality=normalized["data_quality"],
        change_reason=change_reason,
        created_by_user_id=user_id,
        effective_from=normalized["effective_from"],
        metadata_json=_json(
            {
                "engineVersion": THESIS_ENGINE_VERSION,
                "ticker": normalized["ticker"],
                "assetClass": normalized["asset_class"],
                "classification": normalized["classification"],
                "sourceReportId": source_report_id,
            }
        ),
    )
    db.add(thesis_version)
    db.flush()

    evidence_links = _persist_thesis_evidence(
        db,
        user_id=user_id,
        thesis=thesis,
        thesis_version=thesis_version,
        normalized=normalized,
        source_report_id=source_report_id,
        source_engine=source_engine,
    )
    thesis_version.evidence_ids_json = _json([row.id for row in evidence_links])

    thesis.status = _thesis_status_to_parent_status(normalized["thesis_status"])
    thesis.current_version = version_label
    thesis.current_version_id = thesis_version.id
    thesis.current_version_hash = version_hash
    thesis.confidence = _decimal(normalized["confidence"])
    thesis.risk_level = normalized["risk_level"]
    thesis.source_engine = source_engine
    thesis.last_reviewed_at = datetime.now(UTC)
    thesis.next_review_at = normalized["next_review_at"]
    thesis.metadata_json = _json(
        {
            "engineVersion": THESIS_ENGINE_VERSION,
            "sourceReportId": source_report_id,
            "latestClassification": normalized["classification"],
            "evidenceCount": len(evidence_links),
        }
    )
    thesis.updated_at = datetime.now(UTC)
    if commit:
        db.commit()
    return _thesis_result(thesis, thesis_version, created_version=True)


def thesis_to_dict(thesis: AssetThesis, *, include_versions: bool = False) -> dict[str, Any]:
    payload = to_dict(
        AssetThesisContract(
            id=thesis.id,
            ticker=thesis.ticker,
            assetName=thesis.asset_name,
            assetClass=thesis.asset_class,
            thesisType=thesis.thesis_type,
            status=thesis.status,
            currentVersion=thesis.current_version,
            currentVersionId=thesis.current_version_id,
            currentVersionHash=thesis.current_version_hash,
            confidence=_number(thesis.confidence),
            riskLevel=thesis.risk_level,
            versionCount=len(thesis.versions),
        )
    )
    if include_versions:
        payload["versions"] = [thesis_version_to_dict(item) for item in sorted(thesis.versions, key=lambda row: row.created_at or datetime.min, reverse=True)]
    return payload


def thesis_version_to_dict(version: AssetThesisVersion) -> dict[str, Any]:
    return to_dict(
        AssetThesisVersionContract(
            thesisId=version.thesis_id,
            versionId=version.id,
            version=version.version,
            ticker=version.thesis.ticker if version.thesis else "",
            thesisStatus=version.thesis_status,
            role=version.role,
            thesis=version.thesis_text,
            evidenceSummary=version.evidence_summary,
            riskSummary=version.risk_summary,
            monitoringPlan=version.monitoring_plan,
            confidence=_number(version.confidence),
            conviction=_number(version.conviction),
            riskLevel=version.risk_level,
            dataQuality=version.data_quality,
            versionHash=version.version_hash,
            evidenceIds=_json_load(version.evidence_ids_json, []),
            invalidationTriggers=_json_load(version.invalidation_triggers_json, []),
        )
    )


def _normalize_asset_report(db: Session, asset_report: dict[str, Any], *, thesis_type: str) -> dict[str, Any]:
    ticker = str(asset_report.get("ticker") or "").upper().strip()
    asset = _asset_by_ticker(db, ticker)
    asset_class = str(asset_report.get("assetClass") or asset_report.get("class") or (asset.asset_class if asset else "") or "")
    evidence_items = _list(asset_report.get("evidence"))
    risks = _list(asset_report.get("risks"))
    monitoring = _list(asset_report.get("monitoring") or asset_report.get("watchpoints"))
    invalidation = list(dict.fromkeys(risks + DEFAULT_INVALIDATION_TRIGGERS))[:8]
    thesis_text = str(asset_report.get("thesis") or "").strip()
    if not thesis_text:
        thesis_text = f"{ticker} permanece em estudo para {asset_report.get('role') or 'papel estrategico'}."
    return {
        "asset_id": asset.id if asset else None,
        "ticker": ticker,
        "universal_symbol": asset.universal_symbol if asset and asset.universal_symbol else "",
        "asset_name": str(asset_report.get("name") or (asset.name if asset else ticker)),
        "asset_class": asset_class,
        "thesis_type": thesis_type,
        "strategy_profile": str(asset_report.get("strategyProfile") or asset_report.get("role") or ""),
        "thesis_status": _status_from_asset_report(asset_report),
        "role": str(asset_report.get("role") or ""),
        "thesis_text": thesis_text,
        "evidence_summary": _join_sentences(evidence_items),
        "risk_summary": _join_sentences(risks),
        "monitoring_plan": _join_sentences(monitoring or ["Revisar tese, fundamentos, risco e dados no ciclo mensal."]),
        "invalidation_triggers": invalidation,
        "evidence_items": evidence_items,
        "source_engine": "recommended_portfolio_engine",
        "confidence": _number(asset_report.get("confidenceScore"), asset_report.get("institutionalScore"), asset_report.get("alphaScore")),
        "conviction": _number(asset_report.get("institutionalScore"), asset_report.get("alphaScore"), asset_report.get("confidenceScore")),
        "target_weight": _number(asset_report.get("targetWeight")),
        "risk_level": str(asset_report.get("riskLevel") or ""),
        "data_quality": str(asset_report.get("dataQuality") or asset_report.get("dataStatus") or "analisado"),
        "classification": str(asset_report.get("classification") or ""),
        "effective_from": date.today(),
        "next_review_at": _parse_date(asset_report.get("nextReviewDate")),
    }


def _find_or_create_thesis(db: Session, normalized: dict[str, Any], *, source_engine: str) -> AssetThesis:
    thesis = db.execute(
        select(AssetThesis).where(
            AssetThesis.ticker == normalized["ticker"],
            AssetThesis.asset_class == normalized["asset_class"],
            AssetThesis.thesis_type == normalized["thesis_type"],
        )
    ).scalar_one_or_none()
    if thesis:
        return thesis
    thesis = AssetThesis(
        asset_id=normalized["asset_id"],
        ticker=normalized["ticker"],
        universal_symbol=normalized["universal_symbol"],
        asset_name=normalized["asset_name"],
        asset_class=normalized["asset_class"],
        thesis_type=normalized["thesis_type"],
        strategy_profile=normalized["strategy_profile"],
        status="active",
        confidence=_decimal(normalized["confidence"]),
        risk_level=normalized["risk_level"],
        source_engine=source_engine,
        next_review_at=normalized["next_review_at"],
        metadata_json=_json({"engineVersion": THESIS_ENGINE_VERSION}),
    )
    db.add(thesis)
    db.flush()
    return thesis


def _persist_thesis_evidence(
    db: Session,
    *,
    user_id: str | None,
    thesis: AssetThesis,
    thesis_version: AssetThesisVersion,
    normalized: dict[str, Any],
    source_report_id: str,
    source_engine: str,
) -> list[AssetThesisEvidence]:
    specs = [
        ("thesis", "thesis_text", None, normalized["thesis_text"], 86),
        ("thesis", "evidence_summary", None, normalized["evidence_summary"], 82),
        ("thesis", "risk_summary", None, normalized["risk_summary"], 80),
        ("thesis", "confidence", normalized["confidence"], "", 84),
        ("thesis", "conviction", normalized["conviction"], "", 84),
        ("thesis", "target_weight", normalized["target_weight"], "", 78),
    ]
    rows = []
    for domain, field_name, numeric_value, text_value, confidence in specs:
        evidence = record_data_evidence(
            db,
            user_id=user_id,
            asset_id=normalized["asset_id"],
            domain=domain,
            field_name=field_name,
            value_numeric=numeric_value,
            value_text=text_value,
            unit="score" if field_name in {"confidence", "conviction"} else ("pct" if field_name == "target_weight" else ""),
            provider=source_engine,
            source_type="formula" if numeric_value is not None else "system",
            source_ref=f"assetThesis.{normalized['ticker']}.{field_name}",
            formula_name=f"thesis_engine.{field_name}",
            input_payload={
                "ticker": normalized["ticker"],
                "sourceReportId": source_report_id,
                "version": thesis_version.version,
                "versionHash": thesis_version.version_hash,
            },
            confidence=confidence,
            quality_score=confidence,
            status="ok",
            metadata={"thesisId": thesis.id, "thesisVersionId": thesis_version.id},
        )
        link = AssetThesisEvidence(
            thesis_id=thesis.id,
            thesis_version_id=thesis_version.id,
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


def _thesis_result(thesis: AssetThesis, version: AssetThesisVersion | None, *, created_version: bool) -> dict[str, Any]:
    payload = thesis_to_dict(thesis, include_versions=False)
    payload["createdVersion"] = created_version
    payload["version"] = thesis_version_to_dict(version) if version else None
    return payload


def _latest_version(db: Session, thesis_id: str) -> AssetThesisVersion | None:
    return db.execute(
        select(AssetThesisVersion)
        .where(AssetThesisVersion.thesis_id == thesis_id)
        .order_by(desc(AssetThesisVersion.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _next_version_label(db: Session, thesis_id: str) -> str:
    rows = db.execute(select(AssetThesisVersion.version).where(AssetThesisVersion.thesis_id == thesis_id)).scalars().all()
    numbers = []
    for row in rows:
        try:
            numbers.append(int(str(row).lower().replace("v", "")))
        except Exception:
            continue
    return f"v{(max(numbers) if numbers else 0) + 1}"


def _version_hash(normalized: dict[str, Any], *, source_report_id: str, source_engine: str) -> str:
    payload = {
        "ticker": normalized["ticker"],
        "assetClass": normalized["asset_class"],
        "thesisType": normalized["thesis_type"],
        "role": normalized["role"],
        "thesis": normalized["thesis_text"],
        "evidence": normalized["evidence_summary"],
        "risk": normalized["risk_summary"],
        "monitoring": normalized["monitoring_plan"],
        "confidence": round(normalized["confidence"], 4),
        "conviction": round(normalized["conviction"], 4),
        "riskLevel": normalized["risk_level"],
        "sourceReportId": source_report_id,
        "sourceEngine": source_engine,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _status_from_asset_report(asset_report: dict[str, Any]) -> str:
    status = str(asset_report.get("monthlyReviewStatus") or "").lower()
    score = _number(asset_report.get("institutionalScore"), asset_report.get("alphaScore"))
    if status in {"revalidar", "under_review"} or score < 64:
        return "under_review"
    if status in {"acompanhar", "active"}:
        return "active"
    return "draft" if score <= 0 else "active"


def _thesis_status_to_parent_status(status: str) -> str:
    if status in {"under_review", "weakened"}:
        return "under_review"
    if status == "archived":
        return "archived"
    return "active"


def _asset_by_ticker(db: Session, ticker: str) -> Asset | None:
    if not ticker:
        return None
    return db.execute(select(Asset).where(Asset.ticker == ticker)).scalar_one_or_none()


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _join_sentences(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items if item)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_load(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw or "")
    except Exception:
        return fallback


def _number(*values: Any) -> float:
    for value in values:
        try:
            if value in (None, ""):
                continue
            number = float(value)
            if isfinite(number):
                return number
        except Exception:
            continue
    return 0.0


def _decimal(value: Any) -> Decimal:
    return Decimal(str(round(_number(value), 6)))


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None
