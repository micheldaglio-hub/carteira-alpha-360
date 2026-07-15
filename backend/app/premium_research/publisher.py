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
    DataEvidenceLedger,
    PublicationAsset,
    PublicationEvidence,
    PublicationSection,
    PublicationSource,
    PublicationVersion,
    ResearchPublication,
)
from app.premium_research.contracts import (
    PublicationQualityGate,
    PublicationReadinessReport,
    classify_publication_readiness,
    to_dict,
)
from app.premium_research.rating_engine import sync_ratings_for_publication
from app.premium_research.research_committee import run_research_committee_for_publication
from app.premium_research.thesis_engine import sync_theses_from_recommended_report
from app.services.data_lineage import record_data_evidence
from app.services.data_lineage_integrations import record_recommended_portfolio_evidence
from app.services.model_portfolios import get_model_portfolios


PUBLISHER_VERSION = "2026.07.publisher1"
DEFAULT_PUBLICATION_TYPE = "monthly_research"
LEGAL_DISCLAIMER = (
    "Conteudo analitico e informativo para estudo patrimonial. Nao representa recomendacao individual, "
    "ordem de compra ou venda, promessa de rentabilidade ou garantia de resultado. A publicacao premium "
    "exige revisao e aprovacao humana antes de qualquer distribuicao."
)


def create_premium_research_draft(
    db: Session,
    *,
    user_id: str,
    period: str | None = None,
    publication_type: str = DEFAULT_PUBLICATION_TYPE,
    title: str | None = None,
    source_payload: dict[str, Any] | None = None,
    refresh_market: bool = False,
    created_by_user_id: str | None = None,
) -> dict[str, Any]:
    """Create a structured premium research draft without UI side effects.

    The publisher does not calculate portfolio recommendations by itself. It
    consumes existing engines, captures their sources/evidence and persists a
    versioned editorial draft that can later go through review, approval and
    publication.
    """

    payload = source_payload or get_model_portfolios(db, user_id=user_id, refresh_market=refresh_market)
    report = payload.get("recommendedPortfolioReport") or {}
    governance = report.get("governanceLedgerV2") or payload.get("recommendationGovernance") or {}
    report_month = period or str(report.get("reportMonth") or date.today().strftime("%Y-%m"))
    version_label = _next_publication_version(db, publication_type, report_month)
    draft_title = title or f"Alpha Premium Research - {report_month}"

    if source_payload is None and report:
        # Reuse the existing lineage integration so the same numbers visible in
        # the product have traceable evidence before becoming editorial content.
        record_recommended_portfolio_evidence(db, user_id, report)

    publication = ResearchPublication(
        publication_type=publication_type,
        period=report_month,
        title=draft_title,
        subtitle=str(report.get("headline") or "Edicao premium em rascunho para revisao humana."),
        reference_date=_parse_date(report.get("lastReviewDate")),
        closing_date=_parse_date(report.get("nextReviewDate")),
        status="processing",
        version=version_label,
        author_user_id=created_by_user_id or user_id,
        legal_disclaimer=LEGAL_DISCLAIMER,
        metadata_json=_json(
            {
                "publisherVersion": PUBLISHER_VERSION,
                "source": "model_portfolios",
                "reportId": report.get("id"),
                "generatedBy": "AlphaResearchPublisher",
            }
        ),
    )
    db.add(publication)
    db.flush()

    version = PublicationVersion(
        publication_id=publication.id,
        version=version_label,
        status="processing",
        created_by_user_id=created_by_user_id or user_id,
    )
    db.add(version)
    db.flush()

    section_rows = _persist_sections(db, publication, version, _build_sections(report, governance, payload))
    source_rows = _persist_sources(db, publication, version, _build_sources(report, governance, payload))
    asset_rows = _persist_assets(db, publication, version, report)
    thesis_sync = sync_theses_from_recommended_report(
        db,
        report,
        publication=publication,
        publication_version=version,
        user_id=created_by_user_id or user_id,
        force_new_version=True,
        commit=False,
    )
    rating_sync = sync_ratings_for_publication(
        db,
        publication=publication,
        publication_version=version,
        user_id=created_by_user_id or user_id,
        force_new_version=True,
        commit=False,
    )
    evidence_rows = _persist_publisher_evidence(
        db,
        user_id=user_id,
        publication=publication,
        version=version,
        sections_by_key={row.section_key: row for row in section_rows},
        report=report,
        governance=governance,
        payload=payload,
    )

    readiness = build_publication_readiness_report(
        publication_id=publication.id,
        version_id=version.id,
        report=report,
        governance=governance,
        section_count=len(section_rows),
        source_count=len(source_rows),
        evidence_count=len(evidence_rows),
        asset_count=len(asset_rows),
    )
    fallback_count = _count_evidence_status(evidence_rows, {"fallback"})
    partial_count = _count_evidence_status(evidence_rows, {"partial", "fallback", "low_confidence"})
    status = "data_pending" if readiness.blockers else "draft"
    publication.confidence = _decimal(readiness.score)
    version.readiness_score = _decimal(readiness.score)
    version.readiness_classification = readiness.classification
    research_committee = run_research_committee_for_publication(
        db,
        publication=publication,
        publication_version=version,
        user_id=created_by_user_id or user_id,
        commit=False,
    )
    version_hash = _hash_payload(
        {
            "publicationType": publication_type,
            "period": report_month,
            "version": version_label,
            "report": _report_hash_payload(report),
            "readiness": to_dict(readiness),
            "sections": [row.section_key for row in section_rows],
            "sources": [row.source_ref for row in source_rows],
            "assets": [row.ticker for row in asset_rows],
            "thesisVersions": [
                row.get("currentVersionId")
                for row in thesis_sync.get("versions", [])
                if row.get("currentVersionId")
            ],
            "ratingVersions": [
                row.get("currentVersionId")
                for row in rating_sync.get("ratings", [])
                if row.get("currentVersionId")
            ],
            "researchCommitteeRunId": research_committee.get("id"),
            "researchCommitteeDecision": research_committee.get("decision"),
            "researchCommitteeScore": research_committee.get("approvalScore"),
        }
    )

    publication.status = status
    publication.confidence = _decimal(readiness.score)
    publication.partial_data_count = partial_count
    publication.fallback_count = fallback_count
    publication.version_hash = version_hash
    publication.changelog_json = _json(
        [
            "Rascunho premium gerado pelo Alpha Research Publisher.",
            "Secoes, fontes e evidencias foram persistidas para revisao humana.",
            "Nenhuma publicacao automatica foi realizada.",
        ]
    )
    publication.updated_at = datetime.now(UTC)

    version.status = status
    version.version_hash = version_hash
    version.readiness_score = _decimal(readiness.score)
    version.readiness_classification = readiness.classification
    version.source_count = len(source_rows)
    version.partial_data_count = partial_count
    version.fallback_count = fallback_count
    version.payload_json = _json(
        {
            "reportId": report.get("id"),
            "reportMonth": report_month,
            "institutionalScore": report.get("institutionalScore"),
            "classification": report.get("classification"),
            "riskLevel": report.get("riskLevel"),
            "readiness": to_dict(readiness),
            "sectionIds": [row.id for row in section_rows],
            "sourceIds": [row.id for row in source_rows],
            "evidenceIds": [row.id for row in evidence_rows],
            "assetIds": [row.id for row in asset_rows],
            "thesisSync": thesis_sync,
            "ratingSync": rating_sync,
            "researchCommittee": research_committee,
        }
    )
    version.changelog_json = publication.changelog_json
    db.commit()

    return publication_to_dict(publication, readiness=readiness)


def build_publication_readiness_report(
    *,
    publication_id: str,
    version_id: str,
    report: dict[str, Any],
    governance: dict[str, Any],
    section_count: int,
    source_count: int,
    evidence_count: int,
    asset_count: int,
) -> PublicationReadinessReport:
    confidence_score = _number(report.get("confidenceScore"))
    institutional_score = _number(report.get("institutionalScore"))
    data_confidence_score = _number(governance.get("dataConfidenceScore"), confidence_score)
    blockers = []
    warnings = []

    gates = [
        _gate(
            "sections",
            "Secoes editoriais estruturadas",
            section_count >= 4,
            f"{section_count} secoes editoriais foram montadas para o rascunho.",
            severity="high",
        ),
        _gate(
            "sources",
            "Fontes declaradas",
            source_count >= 5,
            f"{source_count} fontes internas foram associadas ao rascunho.",
            severity="high",
        ),
        _gate(
            "evidence",
            "Evidencias rastreaveis",
            evidence_count >= 4,
            f"{evidence_count} evidencias foram vinculadas a publicacao.",
            severity="critical",
        ),
        _gate(
            "assets",
            "Ativos citados",
            asset_count >= 1,
            f"{asset_count} ativo(s) aparecem como parte do relatorio.",
            severity="medium",
        ),
        _gate(
            "confidence",
            "Confianca minima do relatorio",
            confidence_score >= 65,
            f"Confianca Alpha do relatorio: {confidence_score:.0f}/100.",
            severity="high",
        ),
        _gate(
            "institutional_score",
            "Score institucional minimo",
            institutional_score >= 70,
            f"Score institucional do relatorio: {institutional_score:.0f}/100.",
            severity="medium",
        ),
        _gate(
            "data_confidence",
            "Confianca dos dados",
            data_confidence_score >= 55,
            f"Data Confidence usado pela governanca: {data_confidence_score:.0f}/100.",
            severity="high",
        ),
        _gate(
            "human_review",
            "Revisao humana obrigatoria",
            False,
            "Rascunho gerado, mas ainda nao revisado nem aprovado por humano.",
            severity="review",
        ),
    ]

    for gate in gates:
        if gate.status == "fail" and gate.severity == "critical":
            blockers.append(gate.reading)
        elif gate.status == "fail":
            warnings.append(gate.reading)

    governance_blockers = [str(item) for item in governance.get("blockers") or []]
    warnings.extend(governance_blockers[:5])
    score = _readiness_score(gates, confidence_score, data_confidence_score, institutional_score, bool(blockers))
    classification = classify_publication_readiness(score, has_blocker=bool(blockers))
    return PublicationReadinessReport(
        publicationId=publication_id,
        versionId=version_id,
        score=score,
        classification=classification,
        gates=gates,
        blockers=blockers,
        warnings=warnings,
    )


def publication_to_dict(publication: ResearchPublication, *, readiness: PublicationReadinessReport | None = None) -> dict[str, Any]:
    versions = sorted(publication.versions, key=lambda item: item.created_at or datetime.min, reverse=True)
    latest = versions[0] if versions else None
    return {
        "id": publication.id,
        "publicationType": publication.publication_type,
        "period": publication.period,
        "title": publication.title,
        "subtitle": publication.subtitle,
        "status": publication.status,
        "version": publication.version,
        "versionHash": publication.version_hash,
        "confidence": _number(publication.confidence),
        "partialDataCount": publication.partial_data_count,
        "fallbackCount": publication.fallback_count,
        "publishedAt": publication.published_at.isoformat() if publication.published_at else "",
        "legalDisclaimer": publication.legal_disclaimer,
        "latestVersionId": latest.id if latest else "",
        "sectionCount": len(publication.sections),
        "sourceCount": len(publication.sources),
        "evidenceCount": len(publication.evidence_links),
        "assetCount": len(publication.assets),
        "readiness": to_dict(readiness) if readiness else None,
        "createdAt": publication.created_at.isoformat() if publication.created_at else "",
        "updatedAt": publication.updated_at.isoformat() if publication.updated_at else "",
    }


def _build_sections(report: dict[str, Any], governance: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    asset_reports = report.get("assetReports") or []
    top_assets = asset_reports[:5]
    blockers = governance.get("blockers") or []
    governance_plain = governance.get("plainLanguage") or []
    score_breakdown = report.get("scoreBreakdown") or {}
    return [
        {
            "key": "executive_summary",
            "title": "Resumo executivo",
            "order": 10,
            "confidence": _number(report.get("confidenceScore"), 70),
            "content": "\n".join(
                [
                    f"# {report.get('headline') or 'Resumo da Carteira Recomendada Alpha'}",
                    "",
                    str(report.get("executiveSummary") or "Rascunho gerado a partir dos motores internos do Carteira Alpha 360."),
                    "",
                    f"Score institucional: {_number(report.get('institutionalScore')):.0f}/100.",
                    f"Classificacao: {report.get('classification') or 'em estudo'}.",
                    f"Risco agregado: {report.get('riskLevel') or 'nao classificado'}.",
                ]
            ),
            "dataGaps": blockers,
        },
        {
            "key": "recommended_portfolio",
            "title": "Carteira recomendada e ativos centrais",
            "order": 20,
            "confidence": _number(report.get("institutionalScore"), 70),
            "content": "\n".join(
                [
                    "# Principais ativos do relatorio",
                    "",
                    *[
                        f"- {item.get('ticker')}: {item.get('role') or 'papel estrategico'}; score { _number(item.get('institutionalScore')):.0f}/100; risco {item.get('riskLevel') or 'nao informado'}."
                        for item in top_assets
                    ],
                    "",
                    "Os pesos e teses representam estudo de carteira-modelo e precisam de revisao humana antes de publicacao.",
                ]
            ),
            "dataGaps": [],
        },
        {
            "key": "evidence_and_confidence",
            "title": "Evidencias e confianca dos dados",
            "order": 30,
            "confidence": _number(report.get("confidenceScore"), 70),
            "content": "\n".join(
                [
                    "# Evidencias e confianca",
                    "",
                    f"Confianca Alpha consolidada: {_number(report.get('confidenceScore')):.0f}/100.",
                    f"Data Confidence da governanca: {_number(governance.get('dataConfidenceScore'), report.get('confidenceScore')):.0f}/100.",
                    "",
                    "Breakdown principal:",
                    *[f"- {key}: {_number(value):.0f}/100." for key, value in score_breakdown.items()],
                ]
            ),
            "dataGaps": blockers,
        },
        {
            "key": "risk_and_governance",
            "title": "Riscos, governanca e pontos de revisao",
            "order": 40,
            "confidence": _number(governance.get("confidenceScore"), report.get("confidenceScore"), 70),
            "content": "\n".join(
                [
                    "# Governanca",
                    "",
                    *[f"- {item}" for item in governance_plain[:5]],
                    "",
                    "Pontos de monitoramento:",
                    *[f"- {item}" for item in (blockers or ["Sem bloqueio critico registrado; revisao humana segue obrigatoria."])],
                ]
            ),
            "dataGaps": blockers,
        },
        {
            "key": "methodology_and_disclosure",
            "title": "Metodologia e avisos",
            "order": 50,
            "confidence": 90,
            "content": "\n".join(
                [
                    "# Metodologia e avisos",
                    "",
                    *[f"- {item}" for item in payload.get("methodology", [])[:6]],
                    "",
                    LEGAL_DISCLAIMER,
                ]
            ),
            "dataGaps": [],
        },
    ]


def _build_sources(report: dict[str, Any], governance: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    source_count = len(report.get("evidenceLedger") or [])
    return [
        {
            "sourceType": "engine",
            "provider": "recommended_portfolio_engine",
            "sourceRef": "recommendedPortfolioReport",
            "title": "Relatorio institucional da Carteira Recomendada Alpha",
            "confidence": _number(report.get("confidenceScore"), 80),
        },
        {
            "sourceType": "engine",
            "provider": "recommendation_governance_engine",
            "sourceRef": "recommendedPortfolioReport.governanceLedgerV2",
            "title": "Governanca de recomendacao e revisao mensal",
            "confidence": _number(governance.get("confidenceScore"), report.get("confidenceScore"), 78),
        },
        {
            "sourceType": "engine",
            "provider": "alpha_confidence_engine",
            "sourceRef": "confidenceReport",
            "title": "Confianca Alpha consolidada",
            "confidence": _number((payload.get("confidenceReport") or {}).get("overallScore"), report.get("confidenceScore"), 78),
        },
        {
            "sourceType": "engine",
            "provider": "data_confidence_engine",
            "sourceRef": "dataConfidenceAudit",
            "title": "Auditoria de confianca dos dados",
            "confidence": _number((payload.get("dataConfidenceAudit") or {}).get("overallScore"), 70),
        },
        {
            "sourceType": "engine",
            "provider": "model_portfolios_service",
            "sourceRef": "modelPortfolios",
            "title": "Payload consolidado de carteiras modelo",
            "confidence": 78,
        },
        {
            "sourceType": "system",
            "provider": "data_lineage_evidence_ledger",
            "sourceRef": "data_evidence_ledger",
            "title": f"Evidence Ledger vinculado ({source_count} evidencias declaradas no relatorio)",
            "confidence": 82 if source_count else 62,
        },
    ]


def _persist_sections(db: Session, publication: ResearchPublication, version: PublicationVersion, sections: list[dict[str, Any]]) -> list[PublicationSection]:
    rows = []
    for item in sections:
        row = PublicationSection(
            publication_id=publication.id,
            version_id=version.id,
            section_key=item["key"],
            title=item["title"],
            section_order=int(item["order"]),
            status="draft" if not item.get("dataGaps") else "partial",
            confidence=_decimal(item.get("confidence")),
            content_markdown=item.get("content") or "",
            content_json=_json({"title": item["title"], "content": item.get("content") or ""}),
            data_gaps_json=_json(item.get("dataGaps") or []),
            requires_human_approval=True,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def _persist_sources(db: Session, publication: ResearchPublication, version: PublicationVersion, sources: list[dict[str, Any]]) -> list[PublicationSource]:
    rows = []
    now = datetime.now(UTC)
    for item in sources:
        row = PublicationSource(
            publication_id=publication.id,
            version_id=version.id,
            source_type=item["sourceType"],
            provider=item["provider"],
            source_ref=item["sourceRef"],
            title=item["title"],
            confidence=_decimal(item.get("confidence")),
            status="ok" if _number(item.get("confidence")) >= 60 else "partial",
            observed_at=now,
            metadata_json=_json({"publisherVersion": PUBLISHER_VERSION}),
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def _persist_assets(db: Session, publication: ResearchPublication, version: PublicationVersion, report: dict[str, Any]) -> list[PublicationAsset]:
    rows = []
    asset_reports = report.get("assetReports") or []
    tickers = [str(item.get("ticker") or "").upper() for item in asset_reports if item.get("ticker")]
    assets = {}
    if tickers:
        assets = {asset.ticker.upper(): asset for asset in db.execute(select(Asset).where(Asset.ticker.in_(tickers))).scalars().all()}
    for item in asset_reports:
        ticker = str(item.get("ticker") or "").upper()
        asset = assets.get(ticker)
        row = PublicationAsset(
            publication_id=publication.id,
            version_id=version.id,
            asset_id=asset.id if asset else None,
            ticker=ticker,
            asset_name=str(item.get("name") or ticker),
            role=str(item.get("role") or ""),
            action="study",
            target_weight=_decimal(item.get("targetWeight")),
            rating=str(item.get("classification") or ""),
            thesis_status=str(item.get("monthlyReviewStatus") or "draft"),
            evidence_ids_json=_json(item.get("evidence") or []),
            metadata_json=_json({"riskLevel": item.get("riskLevel"), "institutionalScore": item.get("institutionalScore")}),
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def _persist_publisher_evidence(
    db: Session,
    *,
    user_id: str,
    publication: ResearchPublication,
    version: PublicationVersion,
    sections_by_key: dict[str, PublicationSection],
    report: dict[str, Any],
    governance: dict[str, Any],
    payload: dict[str, Any],
) -> list[PublicationEvidence]:
    rows = []
    evidence_specs = [
        ("executive_summary", "recommendation", "institutionalScore", report.get("institutionalScore"), "score", "recommended_portfolio_engine", "formula"),
        ("evidence_and_confidence", "recommendation", "confidenceScore", report.get("confidenceScore"), "score", "alpha_confidence_engine", "formula"),
        ("evidence_and_confidence", "recommendation", "dataConfidenceScore", governance.get("dataConfidenceScore"), "score", "data_confidence_engine", "formula"),
        ("recommended_portfolio", "recommendation", "assetCount", len(report.get("assetReports") or []), "count", "recommended_portfolio_engine", "formula"),
        ("risk_and_governance", "recommendation", "governanceBlockerCount", len(governance.get("blockers") or []), "count", "recommendation_governance_engine", "formula"),
        ("methodology_and_disclosure", "compliance", "legalDisclaimer", None, "", "alpha_research_publisher", "system"),
    ]
    for section_key, domain, field_name, numeric_value, unit, provider, source_type in evidence_specs:
        text_value = LEGAL_DISCLAIMER if field_name == "legalDisclaimer" else ""
        evidence = record_data_evidence(
            db,
            user_id=user_id,
            domain=domain,
            field_name=field_name,
            value_numeric=numeric_value,
            value_text=text_value,
            unit=unit,
            provider=provider,
            source_type=source_type,
            source_ref=f"premiumResearch.{section_key}.{field_name}",
            formula_name=f"alpha_research_publisher.{field_name}",
            input_payload=_report_hash_payload(report) | {"governance": _report_hash_payload(governance), "payloadKeys": sorted(payload.keys())},
            confidence=86 if field_name != "legalDisclaimer" else 92,
            quality_score=86 if field_name != "legalDisclaimer" else 92,
            status="ok",
            metadata={"publicationId": publication.id, "versionId": version.id, "sectionKey": section_key},
        )
        section = sections_by_key.get(section_key)
        link = PublicationEvidence(
            publication_id=publication.id,
            version_id=version.id,
            section_id=section.id if section else None,
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

    linked_evidence_ids = {row.evidence_id for row in rows if row.evidence_id}
    latest_recommendation_evidence = _latest_recommendation_evidence(db, user_id, limit=12)
    for evidence in latest_recommendation_evidence:
        if evidence.id in linked_evidence_ids:
            continue
        section = _section_for_evidence(evidence, sections_by_key)
        link = PublicationEvidence(
            publication_id=publication.id,
            version_id=version.id,
            section_id=section.id if section else None,
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
    _attach_section_evidence_ids(sections_by_key.values(), rows)
    return rows


def _attach_section_evidence_ids(sections: Any, evidence_rows: list[PublicationEvidence]) -> None:
    by_section: dict[str, list[str]] = {}
    for row in evidence_rows:
        if row.section_id:
            by_section.setdefault(row.section_id, []).append(row.id)
    for section in sections:
        section.evidence_ids_json = _json(by_section.get(section.id, []))


def _section_for_evidence(evidence: DataEvidenceLedger, sections: dict[str, PublicationSection]) -> PublicationSection | None:
    if evidence.field_name in {"institutionalScore", "scoreBreakdown.corePortfolio", "scoreBreakdown.globalSatellite"}:
        return sections.get("executive_summary")
    if evidence.field_name in {"confidenceScore", "dataConfidenceScore"} or "scoreBreakdown" in evidence.field_name:
        return sections.get("evidence_and_confidence")
    return sections.get("recommended_portfolio")


def _latest_recommendation_evidence(db: Session, user_id: str, *, limit: int) -> list[DataEvidenceLedger]:
    return list(
        db.execute(
            select(DataEvidenceLedger)
            .where(DataEvidenceLedger.user_id == user_id, DataEvidenceLedger.domain == "recommendation")
            .order_by(desc(DataEvidenceLedger.created_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )


def _gate(id_: str, title: str, passed: bool, reading: str, *, severity: str) -> PublicationQualityGate:
    return PublicationQualityGate(
        id=id_,
        title=title,
        status="pass" if passed else "fail",
        severity=severity,
        reading=reading,
    )


def _readiness_score(
    gates: list[PublicationQualityGate],
    confidence_score: float,
    data_confidence_score: float,
    institutional_score: float,
    has_blocker: bool,
) -> float:
    weights = {
        "sections": 14,
        "sources": 14,
        "evidence": 20,
        "assets": 8,
        "confidence": 14,
        "institutional_score": 10,
        "data_confidence": 12,
        "human_review": 8,
    }
    score = 0.0
    for gate in gates:
        weight = weights.get(gate.id, 0)
        if gate.status == "pass":
            score += weight
        elif gate.id == "human_review":
            score += 2
    score += min(8, max(0, confidence_score - 60) * 0.12)
    score += min(5, max(0, data_confidence_score - 55) * 0.08)
    score += min(5, max(0, institutional_score - 70) * 0.08)
    if has_blocker:
        score = min(score, 39)
    else:
        # Drafts without human review should not be classified as publishable.
        score = min(score, 88)
    return round(max(0, min(100, score)), 2)


def _next_publication_version(db: Session, publication_type: str, period: str) -> str:
    rows = db.execute(
        select(ResearchPublication.version).where(
            ResearchPublication.publication_type == publication_type,
            ResearchPublication.period == period,
        )
    ).scalars().all()
    if not rows:
        return "v0.1"
    numbers = []
    for row in rows:
        try:
            numbers.append(int(str(row).lower().replace("v0.", "")))
        except Exception:
            continue
    return f"v0.{(max(numbers) if numbers else len(rows)) + 1}"


def _count_evidence_status(rows: list[PublicationEvidence], statuses: set[str]) -> int:
    count = 0
    for row in rows:
        if row.status in statuses or _number(row.confidence) < 60:
            count += 1
    return count


def _report_hash_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": report.get("id"),
        "reportMonth": report.get("reportMonth"),
        "institutionalScore": report.get("institutionalScore"),
        "confidenceScore": report.get("confidenceScore"),
        "riskLevel": report.get("riskLevel"),
        "assetTickers": [item.get("ticker") for item in report.get("assetReports", [])],
    }


def _hash_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


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
