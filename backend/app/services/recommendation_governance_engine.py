from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from math import isfinite
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, UserPreference


GOVERNANCE_LATEST_KEY = "recommendation_governance:latest"
GOVERNANCE_MONTH_PREFIX = "recommendation_governance:"


def build_recommendation_governance(
    db: Session | None,
    user_id: str | None,
    recommended_report: dict,
    confidence_report: dict,
    data_confidence_audit: dict | None = None,
) -> dict:
    """Create and optionally persist an auditable governance snapshot."""

    today = date.today()
    report_month = str(recommended_report.get("reportMonth") or today.strftime("%Y-%m"))
    review_id = f"alpha-rec-{report_month}-{today.strftime('%Y%m%d')}"
    institutional_score = _float(recommended_report.get("institutionalScore"))
    confidence_score = _float(confidence_report.get("overallScore"))
    data_confidence_score = _float((data_confidence_audit or {}).get("overallScore")) or confidence_score
    asset_reviews = _asset_reviews(db, recommended_report, data_confidence_audit)
    blockers = _blockers(institutional_score, confidence_score, data_confidence_score, data_confidence_audit)
    status = "approved_for_study" if not blockers else "approved_with_monitoring"

    payload = {
        "status": status,
        "title": "Recommendation Governance Engine",
        "reviewId": review_id,
        "version": "2026.07-gov1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "reportMonth": report_month,
        "nextReviewDate": recommended_report.get("nextReviewDate") or _first_day_next_month(today).isoformat(),
        "institutionalScore": round(institutional_score, 2),
        "confidenceScore": round(confidence_score, 2),
        "dataConfidenceScore": round(data_confidence_score, 2),
        "assetCount": len(asset_reviews),
        "assetReviews": asset_reviews,
        "blockers": blockers,
        "decisionPolicy": [
            "Toda carteira recomendada precisa ter tese, risco, evidencia e proxima revisao.",
            "Nenhuma alteracao de carteira e automatica: o motor registra leitura e acompanhamento.",
            "Se a confianca de dados cair, a conviccao da recomendacao tambem cai.",
            "Qualquer troca de ativo deve gerar novo reviewId e nova justificativa.",
        ],
        "governanceChecklist": [
            "Revisar resultados trimestrais, proventos/JCP e endividamento.",
            "Recalcular scores quando provider atualizar fundamentos.",
            "Comparar pesos propostos com concentracao atual do usuario.",
            "Registrar divergencias de fontes antes de elevar conviccao.",
            "Revisar cripto mensalmente; nucleo de acoes/FIIs em ciclo mensal ou por evento relevante.",
        ],
        "extraordinaryReviewTriggers": [
            "Corte relevante de proventos ou JCP.",
            "Aumento material de divida ou deterioracao de lucro recorrente.",
            "Evento corporativo, regulatorio, split, follow-on ou mudanca de controle.",
            "Queda de confianca de dados abaixo de 60/100.",
            "Desvio grande entre preco, fundamentos ou dividendos vindos de fontes diferentes.",
        ],
        "plainLanguage": _plain_language(status, institutional_score, confidence_score, data_confidence_score, len(blockers)),
    }
    if db is not None and user_id:
        _persist_governance_snapshot(db, user_id, report_month, payload)
    return payload


def _asset_reviews(db: Session | None, recommended_report: dict, data_confidence_audit: dict | None) -> list[dict]:
    confidence_by_ticker = {
        row.get("ticker"): row
        for row in (data_confidence_audit or {}).get("assetRows", [])
        if row.get("ticker")
    }
    tickers = [row.get("ticker") for row in recommended_report.get("assetReports", []) if row.get("ticker")]
    assets_by_ticker = _assets_by_ticker(db, tickers)

    reviews = []
    for row in recommended_report.get("assetReports", []):
        ticker = row.get("ticker", "")
        confidence_row = confidence_by_ticker.get(ticker, {})
        asset = assets_by_ticker.get(ticker)
        score = _float(row.get("institutionalScore"))
        data_score = _float(confidence_row.get("score")) or _float(row.get("confidenceScore")) or _float(row.get("dataQuality"))
        review_status = _review_status(score, data_score)
        reviews.append(
            {
                "ticker": ticker,
                "name": row.get("name") or (asset.name if asset else ticker),
                "assetClass": row.get("assetClass") or (asset.asset_class if asset else ""),
                "role": row.get("role", ""),
                "institutionalScore": round(score, 2),
                "dataConfidenceScore": round(data_score, 2),
                "reviewStatus": review_status,
                "classification": row.get("classification", ""),
                "riskLevel": row.get("riskLevel", ""),
                "priceAtReview": round(_float(asset.last_price) if asset else _float(row.get("price")), 4),
                "dataSourceReading": confidence_row.get("mainLimitation") or "Dados principais avaliados pelo relatorio institucional.",
                "thesis": row.get("thesis", ""),
                "reviewAction": row.get("reviewAction") or _review_action(review_status),
                "evidence": (row.get("evidence") or [])[:4],
                "risks": (row.get("risks") or [])[:4],
                "monitoring": (row.get("monitoring") or row.get("watchpoints") or [])[:4],
            }
        )
    return reviews


def _assets_by_ticker(db: Session | None, tickers: list[str]) -> dict[str, Asset]:
    if db is None or not tickers:
        return {}
    rows = db.execute(select(Asset).where(Asset.ticker.in_(tickers))).scalars().all()
    return {asset.ticker: asset for asset in rows}


def _review_status(score: float, data_score: float) -> str:
    if data_score and data_score < 55:
        return "dados_limitam_conviccao"
    if score >= 80 and (data_score >= 65 or data_score == 0):
        return "tese_institucional_ativa"
    if score >= 70:
        return "tese_ativa_com_monitoramento"
    return "tese_em_observacao"


def _review_action(status: str) -> str:
    return {
        "tese_institucional_ativa": "Manter na carteira recomendada e revisar no ciclo mensal.",
        "tese_ativa_com_monitoramento": "Manter no radar institucional com acompanhamento de risco e dados.",
        "dados_limitam_conviccao": "Nao elevar conviccao enquanto fonte, historico ou fundamentos estiverem incompletos.",
        "tese_em_observacao": "Revisar tese antes de aumentar peso no relatorio.",
    }.get(status, "Revisar no ciclo mensal.")


def _blockers(
    institutional_score: float,
    confidence_score: float,
    data_confidence_score: float,
    data_confidence_audit: dict | None,
) -> list[str]:
    items = []
    fallback_assets = int((data_confidence_audit or {}).get("fallbackAssetCount") or 0)
    if institutional_score < 72:
        items.append("Score institucional abaixo da faixa forte.")
    if confidence_score < 70:
        items.append("Confianca Alpha ainda abaixo do nivel desejado.")
    if data_confidence_score and data_confidence_score < 60:
        items.append("Data Confidence da carteira do usuario limita conclusoes individuais.")
    if fallback_assets:
        items.append(f"{fallback_assets} ativo(s) possuem algum campo em fallback, manual ou historico incompleto.")
    return items


def _plain_language(status: str, institutional_score: float, confidence_score: float, data_score: float, blockers: int) -> list[str]:
    return [
        f"A carteira recomendada foi registrada com score institucional {institutional_score:.0f}/100.",
        f"A confianca do relatorio esta em {confidence_score:.0f}/100 e a confianca dos dados da carteira do usuario em {data_score:.0f}/100.",
        "A carteira pode estar aprovada para estudo mesmo quando ainda existem dados a monitorar; isso fica explicito no status.",
        "Cada revisao mensal deve preservar tese, evidencias, riscos e motivo de permanencia ou troca.",
        f"Status atual: {status}. Pontos de monitoramento: {blockers}.",
    ]


def _persist_governance_snapshot(db: Session, user_id: str, report_month: str, payload: dict) -> None:
    latest = _get_preference(db, user_id, GOVERNANCE_LATEST_KEY)
    monthly = _get_preference(db, user_id, f"{GOVERNANCE_MONTH_PREFIX}{report_month}")
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for preference in [latest, monthly]:
        preference.value_json = serialized
        preference.updated_at = datetime.now(UTC)
    try:
        db.commit()
    except Exception:
        db.rollback()


def _get_preference(db: Session, user_id: str, key: str) -> UserPreference:
    preference = db.execute(select(UserPreference).where(UserPreference.user_id == user_id, UserPreference.key == key)).scalar_one_or_none()
    if preference is None:
        preference = UserPreference(user_id=user_id, key=key)
        db.add(preference)
        db.flush()
    return preference


def _first_day_next_month(day: date) -> date:
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _float(value: Any) -> float:
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0.0
    except Exception:
        return 0.0
