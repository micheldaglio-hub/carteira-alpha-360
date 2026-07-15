from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import DataEvidenceLedger


FORMULA_VERSION = "2026.07.13"
CRITICAL_DOMAINS = {
    "portfolio_backtest",
    "financial_projection",
    "market_data",
    "macro_fx",
    "fixed_income",
    "recommendation",
    "dashboard",
    "tax",
    "stress_test",
    "strategy",
    "copilot",
    "premium_research_attribution",
    "premium_research_snapshot",
    "premium_research_artifact",
    "premium_research_pdf",
}
SOURCE_TYPES = {"provider", "cache", "fallback", "manual", "formula", "system", "user_ledger"}


def record_data_evidence(
    db: Session,
    *,
    domain: str,
    field_name: str,
    user_id: str | None = None,
    asset_id: str | None = None,
    value_numeric: float | int | Decimal | None = None,
    value_text: str = "",
    currency: str = "",
    unit: str = "",
    provider: str = "",
    source_type: str = "system",
    source_ref: str = "",
    formula_name: str = "",
    formula_version: str = FORMULA_VERSION,
    input_payload: dict[str, Any] | None = None,
    confidence: float | int | Decimal = 0,
    quality_score: float | int | Decimal = 0,
    status: str = "ok",
    trace_id: str = "",
    metadata: dict[str, Any] | None = None,
    observed_at: datetime | None = None,
) -> DataEvidenceLedger:
    evidence = DataEvidenceLedger(
        user_id=user_id,
        asset_id=asset_id,
        trace_id=trace_id or _trace_id(domain, field_name, user_id, asset_id),
        evidence_key=_evidence_key(domain, field_name, user_id, asset_id),
        domain=domain[:80],
        field_name=field_name[:120],
        value_numeric=_decimal_or_none(value_numeric),
        value_text=str(value_text or ""),
        currency=currency[:8],
        unit=unit[:32],
        provider=provider[:80],
        source_type=_source_type(source_type),
        source_ref=source_ref[:240],
        formula_name=formula_name[:120],
        formula_version=formula_version[:40],
        input_hash=_hash_payload(input_payload or {}),
        confidence=_decimal(confidence),
        quality_score=_decimal(quality_score),
        status=status[:32],
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False, default=str),
        observed_at=observed_at or datetime.now(UTC),
    )
    db.add(evidence)
    db.flush()
    return evidence


def record_evidence_batch(db: Session, rows: list[dict[str, Any]]) -> list[DataEvidenceLedger]:
    evidence_rows = []
    for row in rows:
        evidence_rows.append(record_data_evidence(db, **row))
    return evidence_rows


def list_data_evidence(
    db: Session,
    *,
    user_id: str,
    domain: str | None = None,
    field_name: str | None = None,
    asset_id: str | None = None,
    limit: int = 100,
) -> list[DataEvidenceLedger]:
    stmt = select(DataEvidenceLedger).where(
        (DataEvidenceLedger.user_id == user_id) | (DataEvidenceLedger.user_id.is_(None))
    )
    if domain:
        stmt = stmt.where(DataEvidenceLedger.domain == domain)
    if field_name:
        stmt = stmt.where(DataEvidenceLedger.field_name == field_name)
    if asset_id:
        stmt = stmt.where(DataEvidenceLedger.asset_id == asset_id)
    stmt = stmt.order_by(desc(DataEvidenceLedger.created_at)).limit(limit)
    return list(db.execute(stmt).scalars().all())


def data_lineage_summary(db: Session, *, user_id: str) -> dict:
    visible = (DataEvidenceLedger.user_id == user_id) | (DataEvidenceLedger.user_id.is_(None))
    total = db.execute(select(func.count()).select_from(DataEvidenceLedger).where(visible)).scalar_one()
    fallback = db.execute(
        select(func.count()).select_from(DataEvidenceLedger).where(visible, DataEvidenceLedger.source_type == "fallback")
    ).scalar_one()
    formula = db.execute(
        select(func.count()).select_from(DataEvidenceLedger).where(visible, DataEvidenceLedger.source_type == "formula")
    ).scalar_one()
    low_confidence = db.execute(
        select(func.count()).select_from(DataEvidenceLedger).where(visible, DataEvidenceLedger.confidence < 60)
    ).scalar_one()
    by_domain_rows = db.execute(
        select(DataEvidenceLedger.domain, func.count())
        .where(visible)
        .group_by(DataEvidenceLedger.domain)
        .order_by(DataEvidenceLedger.domain)
    ).all()
    by_source_rows = db.execute(
        select(DataEvidenceLedger.source_type, func.count())
        .where(visible)
        .group_by(DataEvidenceLedger.source_type)
        .order_by(DataEvidenceLedger.source_type)
    ).all()
    score = _lineage_score(total, fallback, low_confidence)
    return {
        "status": "operational",
        "title": "Data Lineage & Evidence Ledger",
        "generatedAt": datetime.now(UTC).isoformat(),
        "score": score,
        "classification": _classification(score),
        "totalEvidence": int(total or 0),
        "fallbackEvidence": int(fallback or 0),
        "formulaEvidence": int(formula or 0),
        "lowConfidenceEvidence": int(low_confidence or 0),
        "byDomain": {domain: count for domain, count in by_domain_rows},
        "bySourceType": {source_type: count for source_type, count in by_source_rows},
        "plainLanguage": [
            f"O sistema possui {int(total or 0)} evidencias rastreadas para os dados visiveis do usuario.",
            f"{int(fallback or 0)} evidencias usam fallback e precisam aparecer com menor confianca.",
            "Cada evidencia guarda fonte, provider, formula, versao, hash dos insumos e horario observado.",
        ],
    }


def evidence_to_dict(row: DataEvidenceLedger) -> dict:
    try:
        metadata = json.loads(row.metadata_json or "{}")
    except json.JSONDecodeError:
        metadata = {}
    return {
        "id": row.id,
        "userId": row.user_id,
        "assetId": row.asset_id,
        "traceId": row.trace_id,
        "evidenceKey": row.evidence_key,
        "domain": row.domain,
        "fieldName": row.field_name,
        "valueNumeric": float(row.value_numeric) if row.value_numeric is not None else None,
        "valueText": row.value_text,
        "currency": row.currency,
        "unit": row.unit,
        "provider": row.provider,
        "sourceType": row.source_type,
        "sourceRef": row.source_ref,
        "formulaName": row.formula_name,
        "formulaVersion": row.formula_version,
        "inputHash": row.input_hash,
        "confidence": float(row.confidence or 0),
        "qualityScore": float(row.quality_score or 0),
        "status": row.status,
        "metadata": metadata,
        "observedAt": row.observed_at.isoformat() if row.observed_at else "",
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def _lineage_score(total: int, fallback: int, low_confidence: int) -> float:
    if total <= 0:
        return 0.0
    penalty = (fallback / total) * 35 + (low_confidence / total) * 25
    return round(max(0, min(100, 100 - penalty)), 2)


def _classification(score: float) -> str:
    if score >= 90:
        return "Rastreabilidade forte"
    if score >= 75:
        return "Rastreabilidade boa"
    if score >= 55:
        return "Rastreabilidade parcial"
    return "Rastreabilidade fraca"


def _evidence_key(domain: str, field_name: str, user_id: str | None, asset_id: str | None) -> str:
    scope = asset_id or user_id or "global"
    return f"{domain}:{field_name}:{scope}"[:160]


def _trace_id(domain: str, field_name: str, user_id: str | None, asset_id: str | None) -> str:
    raw = f"{domain}|{field_name}|{user_id or ''}|{asset_id or ''}|{datetime.now(UTC).isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _hash_payload(payload: dict[str, Any]) -> str:
    if not payload:
        return ""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _source_type(value: str) -> str:
    raw = str(value or "system").lower().strip()
    return raw if raw in SOURCE_TYPES else "system"


def _decimal(value: float | int | Decimal) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _decimal_or_none(value: float | int | Decimal | None) -> Decimal | None:
    if value in (None, ""):
        return None
    return _decimal(value)
