from __future__ import annotations

from datetime import UTC, date, datetime
from math import isfinite
from statistics import mean
from typing import Any


RISK_MAP = {
    "baixo": 88,
    "baixo_moderado": 82,
    "moderado": 72,
    "controlado": 70,
    "alto_controlado": 58,
    "moderado_alto": 54,
    "alto": 36,
    "extremo": 16,
}


def build_recommended_portfolio_report(
    *,
    screener: dict,
    validation: dict,
    confidence_report: dict,
    fii_screener: dict | None = None,
    global_screener: dict | None = None,
    crypto_study: dict | None = None,
    global_backtest: dict | None = None,
    strategy_report: dict | None = None,
) -> dict:
    """Build the institutional report for Carteira Recomendada Alpha.

    The engine consolidates screeners, confidence gates, evidence and risk into
    a monthly governance report. It does not execute trades and does not promise
    performance; it explains why the model portfolio exists and what must be
    reviewed before the next cycle.
    """

    review_dates = _review_dates()
    confidence_by_ticker = _by_ticker(confidence_report.get("assetRows") or [])
    validation_by_ticker = _by_ticker(validation.get("rows") or [])
    core_assets = [
        _asset_report(asset, "Acoes Brasil", confidence_by_ticker, validation_by_ticker)
        for asset in screener.get("portfolio") or []
    ]
    fii_assets = [
        _asset_report(asset, "FIIs", confidence_by_ticker, validation_by_ticker)
        for asset in (fii_screener or {}).get("portfolio") or []
    ]
    global_assets = [
        _asset_report(asset, "Global", confidence_by_ticker, validation_by_ticker)
        for asset in (global_screener or {}).get("portfolio") or []
    ]
    crypto_asset = _crypto_report(crypto_study, confidence_by_ticker) if crypto_study else None
    all_assets = core_assets + fii_assets + global_assets + ([crypto_asset] if crypto_asset else [])

    score_breakdown = _score_breakdown(
        core_assets=core_assets,
        fii_assets=fii_assets,
        global_assets=global_assets,
        crypto_asset=crypto_asset,
        confidence_report=confidence_report,
        global_backtest=global_backtest,
        strategy_report=strategy_report,
    )
    institutional_score = round(
        score_breakdown["corePortfolio"] * 0.34
        + score_breakdown["confidence"] * 0.22
        + score_breakdown["methodology"] * 0.16
        + score_breakdown["diversification"] * 0.12
        + score_breakdown["evidence"] * 0.10
        + score_breakdown["monthlyGovernance"] * 0.06,
        2,
    )
    institutional_score, institutional_caps = _apply_institutional_caps(institutional_score, confidence_report, score_breakdown)
    classification = _classification(institutional_score)
    risk_level = _portfolio_risk(core_assets, fii_assets, global_assets, crypto_asset)

    sections = [
        _portfolio_section(
            "core_b3",
            "Nucleo Brasil - dividendos e setores perenes",
            "Base principal de renda passiva e preservacao patrimonial em empresas brasileiras essenciais.",
            core_assets,
            screener.get("sectorAllocation") or [],
        ),
        _portfolio_section(
            "fiis",
            "Renda imobiliaria - FIIs",
            "Satelite de proventos imobiliarios, ainda dependente de mais historico real por provider.",
            fii_assets,
            (fii_screener or {}).get("segmentAllocation") or [],
        ),
        _portfolio_section(
            "global",
            "Diversificacao global",
            "Exposicao internacional para reduzir dependencia de Brasil e BRL.",
            global_assets,
            (global_screener or {}).get("regionAllocation") or [],
        ),
    ]
    if crypto_asset:
        sections.append(
            _portfolio_section(
                "crypto",
                "Cripto do mes - assimetria controlada",
                "Tese especulativa separada do nucleo patrimonial.",
                [crypto_asset],
                [],
            )
        )

    return {
        "id": f"recommended-portfolio-alpha-{review_dates['reportMonth']}",
        "title": "Recommended Portfolio Engine institucional",
        "status": "institutional_report",
        "version": "2.0",
        "reportMonth": review_dates["reportMonth"],
        "lastReviewDate": review_dates["lastReviewDate"],
        "nextReviewDate": review_dates["nextReviewDate"],
        "reviewCadence": "Mensal, com revisao extraordinaria se houver fato relevante, corte de proventos, deterioracao de fundamentos ou mudanca macro forte.",
        "headline": _headline(institutional_score, risk_level, strategy_report),
        "executiveSummary": _executive_summary(institutional_score, risk_level, score_breakdown, screener, confidence_report, crypto_study),
        "institutionalScore": institutional_score,
        "classification": classification,
        "riskLevel": risk_level,
        "confidenceScore": _number(confidence_report.get("overallScore")),
        "scoreBreakdown": score_breakdown,
        "institutionalCaps": institutional_caps,
        "portfolios": sections,
        "assetReports": sorted(all_assets, key=lambda item: item["institutionalScore"], reverse=True),
        "evidenceLedger": _evidence_ledger(screener, fii_screener, global_screener, crypto_study, global_backtest, confidence_report, strategy_report),
        "riskMatrix": _risk_matrix(core_assets, fii_assets, global_assets, crypto_asset),
        "monthlyReview": _monthly_review(score_breakdown, confidence_report, global_backtest, crypto_study),
        "governanceRules": [
            "Revisar a carteira recomendada uma vez por mes, mesmo quando nada mudar.",
            "Separar nucleo patrimonial, FIIs, global, cripto e pimentas; cada bloco tem risco e funcao diferente.",
            "Aumentar peso so depois de conferir tese, risco, dados, concentracao e objetivo do usuario.",
            "Se uma fonte falhar, reduzir confianca em vez de fingir certeza.",
            "Historico e backtest ajudam a estudar o passado, mas nao viram promessa de retorno futuro.",
        ],
        "allowedLanguage": [
            "Ativo compativel com a tese.",
            "Ativo em revisao.",
            "Ativo com risco elevado.",
            "Peso-alvo de estudo.",
            "Ponto de acompanhamento mensal.",
        ],
        "blockedLanguage": [
            "Compre agora.",
            "Venda agora.",
            "Sem risco.",
            "Retorno garantido.",
            "Pode comprar sem medo.",
        ],
        "disclaimer": (
            "Relatorio analitico institucional para estudo patrimonial. Nao representa recomendacao individual, "
            "ordem automatica, promessa de rentabilidade ou garantia de resultado."
        ),
        "updatedAt": datetime.now(UTC).isoformat(),
    }


def _asset_report(asset: dict, asset_class: str, confidence_by_ticker: dict[str, dict], validation_by_ticker: dict[str, dict]) -> dict:
    ticker = str(asset.get("ticker") or "").upper()
    confidence = confidence_by_ticker.get(ticker, {})
    validation = validation_by_ticker.get(ticker, {})
    alpha_score = _number(asset.get("alphaScore"), validation.get("validationScore"), confidence.get("score"))
    confidence_score = _number(confidence.get("score"), alpha_score)
    data_score = _data_score(asset, confidence, validation)
    risk_score = RISK_MAP.get(str(asset.get("riskLevel") or confidence.get("riskLevel") or "").lower(), 68)
    evidence_score = _evidence_score(asset, confidence, validation)
    institutional_score = round(
        alpha_score * 0.42
        + confidence_score * 0.22
        + data_score * 0.14
        + risk_score * 0.12
        + evidence_score * 0.10,
        2,
    )
    thesis = str(asset.get("thesis") or validation.get("reading") or confidence.get("reading") or "")
    risks = list(dict.fromkeys(list(asset.get("watchpoints") or []) + list(confidence.get("watch") or [])))[:6]
    evidence = _asset_evidence(asset, confidence, validation)
    return {
        "ticker": ticker,
        "name": asset.get("name"),
        "assetClass": asset_class,
        "sector": asset.get("sector") or asset.get("segment") or "",
        "targetWeight": _number(asset.get("targetWeight")),
        "role": asset.get("role") or "Papel estrategico",
        "thesis": thesis,
        "riskLevel": asset.get("riskLevel") or confidence.get("riskLevel") or "moderado",
        "alphaScore": round(alpha_score, 2),
        "confidenceScore": round(confidence_score, 2),
        "institutionalScore": institutional_score,
        "classification": _asset_classification(institutional_score),
        "scoreBreakdown": {
            "alpha": round(alpha_score, 2),
            "confidence": round(confidence_score, 2),
            "data": round(data_score, 2),
            "risk": round(risk_score, 2),
            "evidence": round(evidence_score, 2),
        },
        "evidence": evidence,
        "risks": risks,
        "monitoring": risks[:4] or ["Revisar fundamentos, precos, proventos e peso no ciclo mensal."],
        "dataQuality": confidence.get("dataStatus") or validation.get("dataStatus") or "analisado",
        "reviewAction": _review_action(institutional_score, risks),
        "monthlyReviewStatus": "acompanhar" if institutional_score >= 64 else "revalidar",
    }


def _crypto_report(crypto_study: dict | None, confidence_by_ticker: dict[str, dict]) -> dict | None:
    if not crypto_study:
        return None
    ticker = str(crypto_study.get("ticker") or "").upper()
    confidence = confidence_by_ticker.get(ticker, {})
    research = crypto_study.get("researchReport") or {}
    research_score = _number(crypto_study.get("researchScore"), crypto_study.get("selectionScore"), research.get("researchScore"))
    confidence_score = _number(confidence.get("score"), research_score)
    data_score = 84 if crypto_study.get("dataMode") == "live" else 58
    access_score = 88 if crypto_study.get("binancePairs") else 42
    institutional_score = round(research_score * 0.38 + confidence_score * 0.18 + data_score * 0.16 + access_score * 0.16 + RISK_MAP["extremo"] * 0.12, 2)
    return {
        "ticker": ticker,
        "name": crypto_study.get("name"),
        "assetClass": "Cripto",
        "sector": "Cripto",
        "targetWeight": 0,
        "role": "Assimetria especulativa controlada",
        "thesis": research.get("thesis") or crypto_study.get("thesis") or "",
        "riskLevel": "extremo",
        "alphaScore": round(research_score, 2),
        "confidenceScore": round(confidence_score, 2),
        "institutionalScore": institutional_score,
        "classification": "Especulativa controlada",
        "scoreBreakdown": {
            "research": round(research_score, 2),
            "confidence": round(confidence_score, 2),
            "data": round(data_score, 2),
            "access": round(access_score, 2),
            "risk": RISK_MAP["extremo"],
        },
        "evidence": [
            f"Selecionada pelo Screener Alpha Crypto como {crypto_study.get('decisionLabel') or 'oportunidade mensal'}.",
            f"Acesso Binance: {', '.join(crypto_study.get('binancePairs') or []) or 'nao confirmado'}.",
            f"Research Score {research_score:.1f}/100.",
        ],
        "risks": list(research.get("riskFactors") or crypto_study.get("watchpoints") or [])[:6],
        "monitoring": list(crypto_study.get("monthlyScanCriteria") or [])[:4],
        "dataQuality": crypto_study.get("dataMode") or "fallback",
        "reviewAction": "Manter como tese pequena e revisar mensalmente liquidez, narrativa, tokenomics e risco.",
        "monthlyReviewStatus": "revalidar",
    }


def _portfolio_section(section_id: str, title: str, thesis: str, assets: list[dict], allocation: list[dict]) -> dict:
    target_weight = round(sum(_number(item.get("targetWeight")) for item in assets), 2)
    score = _average([item.get("institutionalScore") for item in assets])
    return {
        "id": section_id,
        "title": title,
        "thesis": thesis,
        "assetCount": len(assets),
        "targetWeight": target_weight,
        "score": score,
        "classification": _classification(score),
        "allocation": allocation,
        "topAssets": assets[:5],
    }


def _score_breakdown(
    *,
    core_assets: list[dict],
    fii_assets: list[dict],
    global_assets: list[dict],
    crypto_asset: dict | None,
    confidence_report: dict,
    global_backtest: dict | None,
    strategy_report: dict | None,
) -> dict:
    gates = confidence_report.get("gates") or []
    methodology_gate = _find_gate(gates, "methodology")
    data_gate = _find_gate(gates, "data_coverage")
    source_gate = _find_gate(gates, "sources")
    backtest_gate = _find_gate(gates, "backtest")
    diversification_gate = _find_gate(gates, "diversification")
    core_score = _average([item.get("institutionalScore") for item in core_assets])
    fii_score = _average([item.get("institutionalScore") for item in fii_assets])
    global_score = _average([item.get("institutionalScore") for item in global_assets])
    crypto_score = _number((crypto_asset or {}).get("institutionalScore"))
    evidence = _average([data_gate, source_gate, backtest_gate])
    global_rows = len((global_backtest or {}).get("rows") or [])
    governance = 72 + min(16, len(gates) * 2) + (6 if global_rows >= 6 else 0)
    if strategy_report and strategy_report.get("status") == "operacional":
        governance += 4
    return {
        "corePortfolio": round(core_score, 2),
        "fiiSatellite": round(fii_score, 2),
        "globalSatellite": round(global_score, 2),
        "cryptoSatellite": round(crypto_score, 2),
        "confidence": round(_number(confidence_report.get("overallScore")), 2),
        "methodology": round(methodology_gate or 0, 2),
        "diversification": round(diversification_gate or 0, 2),
        "evidence": round(evidence, 2),
        "monthlyGovernance": round(_clamp(governance), 2),
    }


def _apply_institutional_caps(score: float, confidence_report: dict, score_breakdown: dict) -> tuple[float, list[str]]:
    capped = float(score)
    reasons = list(confidence_report.get("confidenceCaps") or [])
    confidence = _number(confidence_report.get("overallScore"))
    if confidence and confidence < 70:
        capped = min(capped, 69.0)
        reasons.append("A confianca Alpha consolidada abaixo de 70 impede leitura institucional forte.")
    if score_breakdown.get("evidence", 0) < 70:
        capped = min(capped, 74.0)
        reasons.append("Evidencias e backtests abaixo de 70 limitam o relatorio a acompanhamento.")
    if score_breakdown.get("diversification", 0) < 60:
        capped = min(capped, 74.0)
        reasons.append("Diversificacao abaixo de 60 impede score institucional alto.")
    if reasons:
        capped = min(capped, 79.0)
    return round(capped, 2), list(dict.fromkeys(reasons))


def _evidence_ledger(
    screener: dict,
    fii_screener: dict | None,
    global_screener: dict | None,
    crypto_study: dict | None,
    global_backtest: dict | None,
    confidence_report: dict,
    strategy_report: dict | None,
) -> list[dict]:
    rows = [
        _ledger("screener_alpha_b3", "Screener Alpha B3", "Seleciona o nucleo Brasil por setores perenes, qualidade, liquidez, risco e proventos.", screener.get("updatedAt"), 82),
        _ledger("confidence_engine", "Alpha Confidence Engine", "Audita gates de dados, metodologia, fundamentos, risco, diversificacao, backtest e fontes.", confidence_report.get("updatedAt"), _number(confidence_report.get("overallScore"))),
    ]
    if fii_screener:
        rows.append(_ledger("screener_fiis", "Screener Alpha FIIs", "Classifica fundos imobiliarios por renda, qualidade do portfolio, gestao, liquidez e risco.", fii_screener.get("updatedAt"), 68))
    if global_screener:
        rows.append(_ledger("screener_global", "Screener Alpha Global", "Monta watchlist internacional por pais, moeda, setor, qualidade e diversificacao.", global_screener.get("updatedAt"), 70))
    if global_backtest:
        rows.append(_ledger("global_backtest", "Global Backtest Engine", "Compara stock direto, BDR proxy e ETF global em BRL com cambio.", global_backtest.get("updatedAt"), 64 if global_backtest.get("warnings") else 74))
    if crypto_study:
        rows.append(_ledger("crypto_research", "Crypto Research Engine", "Valida cripto do mes por liquidez, narrativa, tokenomics, acesso e risco.", crypto_study.get("updatedAt"), _number(crypto_study.get("researchScore"), crypto_study.get("selectionScore"))))
    if strategy_report:
        rows.append(_ledger("strategy_engine", "Strategy Engine 2.0", "Compara a carteira com perfis patrimoniais e alocacoes alvo.", strategy_report.get("updatedAt"), _number(strategy_report.get("primaryScore"))))
    return rows


def _ledger(source_id: str, title: str, reading: str, as_of: str | None, confidence: float) -> dict:
    return {
        "id": source_id,
        "title": title,
        "reading": reading,
        "asOf": as_of or datetime.now(UTC).isoformat(),
        "confidenceScore": round(_clamp(confidence), 2),
    }


def _risk_matrix(core_assets: list[dict], fii_assets: list[dict], global_assets: list[dict], crypto_asset: dict | None) -> list[dict]:
    all_assets = core_assets + fii_assets + global_assets + ([crypto_asset] if crypto_asset else [])
    high_risk = [item for item in all_assets if str(item.get("riskLevel") or "").lower() in {"alto", "moderado_alto", "extremo"}]
    low_data = [item for item in all_assets if item.get("dataQuality") in {"fallback", "foundation", "foundation_watchlist", "foundation_internal_universe"}]
    return [
        {
            "id": "core_concentration",
            "title": "Concentracao do nucleo",
            "severity": "media" if max((_number(item.get("targetWeight")) for item in core_assets), default=0) <= 13 else "alta",
            "reading": "O nucleo Brasil tem pesos distribuidos, mas energia e setores regulados precisam de acompanhamento macro e politico.",
        },
        {
            "id": "data_quality",
            "title": "Qualidade dos dados",
            "severity": "media" if low_data else "baixa",
            "reading": f"{len(low_data)} ativos ou blocos ainda usam base inicial/fallback e devem ganhar dados historicos reais.",
        },
        {
            "id": "high_risk_assets",
            "title": "Risco elevado",
            "severity": "alta" if high_risk else "baixa",
            "reading": f"{len(high_risk)} ativos/blocos exigem cuidado adicional, especialmente cripto e ativos com risco politico.",
        },
        {
            "id": "global_execution",
            "title": "Execucao internacional",
            "severity": "media",
            "reading": "A carteira global precisa comparar stock direto, BDR, ETF, cambio, imposto e corretora antes da execucao.",
        },
    ]


def _monthly_review(score_breakdown: dict, confidence_report: dict, global_backtest: dict | None, crypto_study: dict | None) -> dict:
    checklist = [
        "Atualizar precos, fundamentos, dividendos/JCP e eventos corporativos.",
        "Recalcular Screener Alpha B3 e comparar pesos atuais versus pesos oficiais.",
        "Revisar se algum ativo cortou proventos, aumentou divida ou piorou resultado.",
        "Atualizar FIIs com vacancia, rendimentos, P/VP, gestao e liquidez.",
        "Atualizar carteira global com cambio, dividendos internacionais e risco de moeda.",
        "Revalidar cripto do mes com Binance, CoinMarketCap, CoinGecko e Research Engine.",
        "Registrar qualquer mudanca de tese no changelog e na documentacao tecnica.",
    ]
    blockers = []
    if score_breakdown.get("evidence", 0) < 70:
        blockers.append("Evidencias ainda limitam a confianca institucional.")
    if (confidence_report.get("overallScore") or 0) < 70:
        blockers.append("Confianca Alpha abaixo do ideal para comunicacao forte.")
    if (global_backtest or {}).get("warnings"):
        blockers.append("Backtest global possui avisos/fallbacks que precisam ser revisados.")
    if crypto_study and crypto_study.get("riskLevel") == "extremo":
        blockers.append("Cripto continua fora do nucleo e precisa de limite de exposicao.")
    return {
        "status": "pronto_para_revisao_mensal" if not blockers else "revisao_com_pontos_de_atencao",
        "checklist": checklist,
        "blockers": blockers,
        "outputExpected": [
            "Manter tese.",
            "Reduzir confianca.",
            "Rebalancear pesos-alvo de estudo.",
            "Mover ativo para observacao.",
            "Substituir ativo no proximo ciclo se os criterios deixarem de ser atendidos.",
        ],
    }


def _executive_summary(score: float, risk_level: str, breakdown: dict, screener: dict, confidence_report: dict, crypto_study: dict | None) -> list[str]:
    selected = len(screener.get("portfolio") or [])
    summary = [
        f"A Carteira Recomendada Alpha tem score institucional de {score:.0f}/100 e classificacao { _classification(score).lower() }.",
        f"O nucleo Brasil tem {selected} ativos, com foco em setores perenes, proventos e preservacao patrimonial.",
        f"A confianca Alpha consolidada esta em { _number(confidence_report.get('overallScore')):.0f}/100.",
        f"O risco agregado foi classificado como {risk_level}.",
    ]
    if breakdown.get("globalSatellite", 0) > 0:
        summary.append("A diversificacao internacional ja aparece como satelite, mas exige comparacao entre stock, BDR e ETF antes da execucao.")
    if crypto_study:
        summary.append(f"A cripto do mes ({crypto_study.get('ticker')}) fica separada do nucleo e deve ser revisada mensalmente.")
    return summary


def _headline(score: float, risk_level: str, strategy_report: dict | None) -> str:
    strategy = ""
    if strategy_report and strategy_report.get("primaryStrategy"):
        strategy = f" Perfil estrategico mais proximo: {strategy_report.get('primaryStrategy')}."
    if score >= 82:
        return f"Carteira Recomendada Alpha esta em nivel institucional forte, com risco {risk_level}.{strategy}"
    if score >= 70:
        return f"Carteira Recomendada Alpha esta adequada para estudo institucional, com pontos de revisao mensal e risco {risk_level}.{strategy}"
    return f"Carteira Recomendada Alpha ainda exige reforco de evidencias antes de ser tratada como forte, com risco {risk_level}.{strategy}"


def _portfolio_risk(core_assets: list[dict], fii_assets: list[dict], global_assets: list[dict], crypto_asset: dict | None) -> str:
    all_assets = core_assets + fii_assets + global_assets + ([crypto_asset] if crypto_asset else [])
    average_risk = _average([RISK_MAP.get(str(item.get("riskLevel") or "").lower(), 68) for item in all_assets])
    crypto_penalty = 8 if crypto_asset else 0
    adjusted = average_risk - crypto_penalty
    if adjusted >= 78:
        return "moderado_conservador"
    if adjusted >= 66:
        return "moderado"
    if adjusted >= 52:
        return "moderado_arrojado"
    return "arrojado_controlado"


def _asset_evidence(asset: dict, confidence: dict, validation: dict) -> list[str]:
    evidence = []
    evidence.extend(str(item) for item in asset.get("whySelected") or [])
    evidence.extend(str(item) for item in confidence.get("passed") or [])
    if validation.get("reading"):
        evidence.append(str(validation["reading"]))
    if asset.get("alphaReading"):
        evidence.append(str(asset["alphaReading"]))
    if not evidence and asset.get("thesis"):
        evidence.append(str(asset["thesis"]))
    return list(dict.fromkeys(evidence))[:6]


def _evidence_score(asset: dict, confidence: dict, validation: dict) -> float:
    count = len(_asset_evidence(asset, confidence, validation))
    score = 48 + min(32, count * 8)
    if asset.get("dataFields"):
        score += min(12, _number(asset.get("dataFields")) * 2)
    if confidence.get("score"):
        score += 6
    return _clamp(score)


def _data_score(asset: dict, confidence: dict, validation: dict) -> float:
    fields = _number(asset.get("dataFields"), validation.get("dataFields"))
    data_status = str(confidence.get("dataStatus") or validation.get("dataStatus") or asset.get("dataStatus") or "").lower()
    base = 80 if data_status in {"live", "provider_validated", "brapi_universe"} else 66 if data_status in {"analisado", "partial_provider_data"} else 56
    return _clamp(base + min(16, fields * 2))


def _review_action(score: float, risks: list[str]) -> str:
    if score >= 82 and len(risks) <= 3:
        return "Manter no nucleo do estudo e revisar mensalmente fundamentos, proventos e peso."
    if score >= 68:
        return "Manter em acompanhamento institucional e revisar os pontos de risco antes de aumentar exposicao."
    return "Revalidar tese, dados e risco antes de manter peso relevante na carteira recomendada."


def _asset_classification(score: float) -> str:
    if score >= 84:
        return "Nucleo institucional"
    if score >= 74:
        return "Alta confianca Alpha"
    if score >= 64:
        return "Confianca monitorada"
    return "Revalidar tese"


def _classification(score: float) -> str:
    if score >= 84:
        return "Institucional forte"
    if score >= 74:
        return "Institucional em bom nivel"
    if score >= 64:
        return "Institucional em construcao"
    return "Revisao obrigatoria"


def _find_gate(gates: list[dict], gate_id: str) -> float:
    for gate in gates:
        if gate.get("id") == gate_id:
            return _number(gate.get("score"))
    return 0.0


def _review_dates() -> dict[str, str]:
    today = date.today()
    first_day = today.replace(day=1)
    next_month = first_day.replace(year=first_day.year + 1, month=1) if first_day.month == 12 else first_day.replace(month=first_day.month + 1)
    return {
        "reportMonth": f"{today.year}-{today.month:02d}",
        "lastReviewDate": first_day.isoformat(),
        "nextReviewDate": next_month.isoformat(),
    }


def _by_ticker(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("ticker") or "").upper(): row for row in rows if row.get("ticker")}


def _average(values: list[Any]) -> float:
    clean = [_number(value) for value in values if _number(value) > 0]
    return round(mean(clean), 2) if clean else 0.0


def _number(*values: Any) -> float:
    for value in values:
        if value is None or value == "":
            continue
        try:
            number = float(value)
            if isfinite(number):
                return number
        except Exception:
            continue
    return 0.0


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))
