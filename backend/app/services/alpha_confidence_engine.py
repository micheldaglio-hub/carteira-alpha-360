from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from statistics import mean
from typing import Any


RISK_SCORE = {
    "baixo": 92,
    "baixo_moderado": 86,
    "moderado": 74,
    "controlado": 72,
    "alto_controlado": 58,
    "moderado_alto": 56,
    "alto": 38,
    "extremo": 18,
}


def build_alpha_confidence_report(
    *,
    screener: dict,
    validation: dict,
    fii_screener: dict | None = None,
    global_screener: dict | None = None,
    crypto_study: dict | None = None,
    global_backtest: dict | None = None,
    imported_backtest: dict | None = None,
) -> dict:
    """Build an auditable confidence layer for the model portfolios.

    This engine does not decide what to buy or sell. It grades whether the current
    analytical package has enough data, risk controls and diversification to be
    presented with confidence inside Carteira Alpha 360.
    """

    b3_assets = list(screener.get("portfolio") or [])
    asset_rows = [_asset_confidence(asset, "Acoes Brasil", data_mode=_b3_data_mode(screener)) for asset in b3_assets]

    for asset in (fii_screener or {}).get("portfolio") or []:
        asset_rows.append(_asset_confidence(asset, "FIIs", data_mode="foundation"))

    for asset in (global_screener or {}).get("portfolio") or []:
        asset_rows.append(_asset_confidence(asset, "Global", data_mode=asset.get("dataStatus") or (global_screener or {}).get("dataMode")))

    if crypto_study:
        asset_rows.append(_crypto_confidence(crypto_study))

    gates = [
        _gate_data_coverage(screener, validation, fii_screener, global_screener, crypto_study),
        _gate_methodology(screener, fii_screener, global_screener, crypto_study),
        _gate_fundamentals(asset_rows),
        _gate_risk(asset_rows),
        _gate_diversification(b3_assets, (fii_screener or {}).get("portfolio") or [], (global_screener or {}).get("portfolio") or []),
        _gate_backtests(global_backtest, imported_backtest),
        _gate_sources(screener, global_screener, crypto_study),
    ]

    asset_score = _average([row["score"] for row in asset_rows]) if asset_rows else 0
    gate_score = _average([gate["score"] for gate in gates]) if gates else 0
    core_score = _average([row["score"] for row in asset_rows if row["assetClass"] == "Acoes Brasil"]) or asset_score
    overall = round(core_score * 0.42 + gate_score * 0.40 + asset_score * 0.18, 2)
    overall, cap_reasons = _apply_confidence_caps(overall, gates, asset_rows, global_backtest, crypto_study)
    classification = _classification(overall)

    return {
        "title": "Confiabilidade Alpha",
        "status": "confidence_layer",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "overallScore": overall,
        "classification": classification,
        "headline": _headline(overall, gates),
        "plainLanguage": _plain_language(overall, gates, crypto_study),
        "confidenceCaps": cap_reasons,
        "gates": gates,
        "assetRows": sorted(asset_rows, key=lambda item: item["score"], reverse=True),
        "nonNegotiables": [
            "Nenhum ativo e tratado como compra sem medo.",
            "Sem dados suficientes, o ativo nao sobe para alta confianca Alpha.",
            "Cripto fica fora do nucleo patrimonial e sempre recebe leitura de risco extremo.",
            "Concentracao individual, setorial ou geografica reduz a confianca mesmo quando o ativo e bom.",
            "Backtest ajuda a entender o passado, mas nunca vira promessa de rentabilidade futura.",
        ],
        "howToRead": (
            "A nota mostra o quanto a indicacao esta bem sustentada por dados, criterios e controles. "
            "Ela aumenta a confianca analitica, mas nao elimina risco de mercado, risco de empresa, risco regulatorio ou erro de premissa."
        ),
    }


def _asset_confidence(asset: dict, asset_class: str, *, data_mode: str | None = None) -> dict:
    alpha_score = _number(asset.get("alphaScore"), asset.get("validationScore"))
    data_fields = _number(asset.get("dataFields"))
    target_weight = _number(asset.get("targetWeight"))
    risk_score = RISK_SCORE.get(str(asset.get("riskLevel") or "").lower(), 68)
    data_score = _data_score(data_mode, data_fields)
    allocation_score = _allocation_score(target_weight)
    score = round(alpha_score * 0.50 + data_score * 0.20 + risk_score * 0.18 + allocation_score * 0.12, 2)
    classification = _asset_classification(score, asset.get("riskLevel"))
    watchpoints = list(asset.get("watchpoints") or [])
    passed = [
        f"Score Alpha {alpha_score:.1f}/100.",
        f"Peso alvo {target_weight:.1f}% dentro do modelo.",
        f"Papel na carteira: {asset.get('role') or asset.get('conviction') or 'estrategico'}.",
    ]
    if data_fields:
        passed.append(f"{int(data_fields)} campos de dados considerados.")
    if data_mode:
        passed.append(f"Modo de dados: {data_mode}.")
    return {
        "ticker": asset.get("ticker"),
        "name": asset.get("name"),
        "assetClass": asset_class,
        "score": score,
        "classification": classification,
        "status": _asset_status(score),
        "targetWeight": target_weight,
        "riskLevel": asset.get("riskLevel"),
        "dataStatus": data_mode or asset.get("dataStatus") or "analisado",
        "passed": passed,
        "watch": watchpoints[:4],
        "reading": _asset_reading(asset, asset_class, score, classification),
    }


def _crypto_confidence(study: dict) -> dict:
    research_score = _number(study.get("researchScore"), study.get("selectionScore"))
    data_score = 84 if study.get("dataMode") == "live" else 58
    exchange_score = 86 if study.get("binancePairs") else 35
    risk_score = RISK_SCORE["extremo"]
    score = round(research_score * 0.36 + data_score * 0.22 + exchange_score * 0.22 + risk_score * 0.20, 2)
    classification = "Especulativa controlada" if score >= 60 else "Especulativa em validacao"
    return {
        "ticker": study.get("ticker"),
        "name": study.get("name"),
        "assetClass": "Cripto",
        "score": score,
        "classification": classification,
        "status": "attention",
        "targetWeight": 0,
        "riskLevel": "extremo",
        "dataStatus": study.get("dataMode") or "fallback",
        "passed": [
            f"Research Score {research_score:.1f}/100.",
            f"Acesso operacional: {', '.join(study.get('binancePairs') or []) or 'nao confirmado'}.",
            "Separada do nucleo patrimonial.",
        ],
        "watch": list(study.get("watchpoints") or [])[:4],
        "reading": (
            f"{study.get('ticker')} aparece como oportunidade especulativa mensal. "
            "Mesmo passando no research, continua sendo risco extremo e exige exposicao pequena."
        ),
    }


def _gate_data_coverage(screener: dict, validation: dict, fii_screener: dict | None, global_screener: dict | None, crypto_study: dict | None) -> dict:
    selected = _number(screener.get("selectedCount")) or len(screener.get("portfolio") or [])
    candidate_count = _number(screener.get("candidateCount"))
    data_rows = validation.get("rows") or []
    avg_fields = _average([_number(row.get("dataFields")) for row in data_rows])
    live_crypto = crypto_study and crypto_study.get("dataMode") == "live"
    global_data = (global_screener or {}).get("dataMode") == "provider_validated"
    score = 58
    if selected >= 10:
        score += 8
    if candidate_count >= selected:
        score += 8
    if avg_fields >= 6:
        score += 12
    elif avg_fields >= 1:
        score += 6
    if live_crypto:
        score += 6
    if global_data:
        score += 6
    if fii_screener:
        score += 4
    score = _clamp(score)
    return _gate(
        "data_coverage",
        "Cobertura de dados",
        score,
        "O Alpha cruza universo B3, dados internos, FIIs, global e cripto antes de consolidar a leitura.",
        "Quanto mais provider real e historico validado, maior a confianca.",
    )


def _gate_methodology(screener: dict, fii_screener: dict | None, global_screener: dict | None, crypto_study: dict | None) -> dict:
    filters = len(screener.get("filters") or []) + len((fii_screener or {}).get("filters") or []) + len((global_screener or {}).get("filters") or [])
    has_crypto_research = bool((crypto_study or {}).get("researchReport"))
    score = 66 + min(18, filters * 2) + (8 if has_crypto_research else 0)
    return _gate(
        "methodology",
        "Metodologia",
        _clamp(score),
        "A selecao usa criterios objetivos: setor, qualidade, liquidez, governanca, risco, proventos e papel na carteira.",
        "A cada nova fonte, a metodologia deve registrar o que mudou.",
    )


def _gate_fundamentals(asset_rows: list[dict]) -> dict:
    core_rows = [row for row in asset_rows if row["assetClass"] in {"Acoes Brasil", "FIIs", "Global"}]
    score = _average([row["score"] for row in core_rows])
    return _gate(
        "fundamentals",
        "Fundamentos",
        score,
        "Os ativos do nucleo passam por score de qualidade, perenidade, liquidez e risco.",
        "Empresas boas ainda podem ficar caras, reduzir proventos ou piorar fundamentos.",
    )


def _gate_risk(asset_rows: list[dict]) -> dict:
    high_risk = [row for row in asset_rows if str(row.get("riskLevel") or "").lower() in {"alto", "alto_controlado", "moderado_alto", "extremo"}]
    core_high = [row for row in high_risk if row["assetClass"] != "Cripto"]
    score = 88 - len(core_high) * 7
    if any(row["assetClass"] == "Cripto" for row in high_risk):
        score -= 4
    return _gate(
        "risk",
        "Controle de risco",
        _clamp(score),
        "O Alpha penaliza risco politico, alavancagem, baixa liquidez, tese fraca e cripto fora do tamanho adequado.",
        "Risco nao desaparece; ele precisa aparecer na tela antes da decisao.",
    )


def _gate_diversification(b3_assets: list[dict], fii_assets: list[dict], global_assets: list[dict]) -> dict:
    sectors = {}
    for asset in b3_assets:
        sectors[asset.get("sector") or "Nao classificado"] = sectors.get(asset.get("sector") or "Nao classificado", 0) + _number(asset.get("targetWeight"))
    max_sector = max(sectors.values(), default=100)
    selected = len(b3_assets)
    score = 62 + min(18, selected * 1.4)
    if max_sector <= 35:
        score += 14
    elif max_sector <= 45:
        score += 8
    else:
        score -= 10
    if fii_assets:
        score += 4
    if global_assets:
        score += 4
    return _gate(
        "diversification",
        "Diversificacao",
        _clamp(score),
        f"A carteira principal tem {selected} ativos e maior setor em {max_sector:.1f}%.",
        "O proximo salto de confianca vem de global, FIIs e moeda estrangeira com dados historicos robustos.",
    )


def _gate_backtests(global_backtest: dict | None, imported_backtest: dict | None) -> dict:
    has_global_rows = len((global_backtest or {}).get("rows") or []) >= 6
    has_imported_rows = len((imported_backtest or {}).get("rows") or []) >= 6
    warnings = len((global_backtest or {}).get("warnings") or [])
    score = 55 + (16 if has_global_rows else 0) + (14 if has_imported_rows else 0) - min(12, warnings * 3)
    return _gate(
        "backtest",
        "Historico e cenarios",
        _clamp(score),
        "O sistema compara cenarios historicos e separa resultado passado de promessa futura.",
        "Backtests com fallback ajudam no desenho, mas precisam de historico real para virar evidencia forte.",
    )


def _gate_sources(screener: dict, global_screener: dict | None, crypto_study: dict | None) -> dict:
    source_score = 62
    if screener.get("universeSource") == "brapi_available":
        source_score += 12
    if (global_screener or {}).get("dataMode") == "provider_validated":
        source_score += 10
    if (crypto_study or {}).get("dataMode") == "live":
        source_score += 10
    return _gate(
        "sources",
        "Fontes e rastreabilidade",
        _clamp(source_score),
        "A indicacao precisa apontar de onde vieram universo, preco, fundamentos e research.",
        "Quando provider falha, o Alpha deve avisar e reduzir confianca.",
    )


def _apply_confidence_caps(score: float, gates: list[dict], asset_rows: list[dict], global_backtest: dict | None, crypto_study: dict | None) -> tuple[float, list[str]]:
    capped = float(score)
    reasons: list[str] = []
    by_id = {gate["id"]: gate for gate in gates}
    data_score = _number((by_id.get("data_coverage") or {}).get("score"))
    risk_score = _number((by_id.get("risk") or {}).get("score"))
    fundamentals_score = _number((by_id.get("fundamentals") or {}).get("score"))
    source_score = _number((by_id.get("sources") or {}).get("score"))

    if data_score and data_score < 80:
        capped = min(capped, 69.0)
        reasons.append("Cobertura de dados abaixo de 80 limita a confianca maxima a 69/100.")
    if risk_score and risk_score < 60:
        capped = min(capped, 74.0)
        reasons.append("Controle de risco abaixo de 60 impede classificacao institucional forte.")
    if fundamentals_score and fundamentals_score < 64:
        capped = min(capped, 69.0)
        reasons.append("Fundamentos essenciais incompletos mantem a leitura como provisional.")
    fallback_assets = [
        row
        for row in asset_rows
        if str(row.get("dataStatus") or "").lower() in {"fallback", "foundation", "foundation_watchlist", "foundation_internal_universe", "alpha_fallback"}
    ]
    has_backtest_fallback = bool([item for item in (global_backtest or {}).get("warnings") or [] if "fallback" in str(item).lower()])
    if fallback_assets or has_backtest_fallback:
        capped = min(capped, 79.0)
        reasons.append("Uso relevante de fallback deixa o relatorio em modo provisional ate novas fontes reais validarem o historico.")
    if source_score and source_score < 65 and crypto_study:
        capped = min(capped, 78.0)
        reasons.append("Fontes recentes/noticias insuficientes reduzem confianca apenas para leituras sensiveis a eventos recentes.")
    return round(capped, 2), reasons


def _gate(key: str, label: str, score: float, reading: str, limitation: str) -> dict:
    score = round(_clamp(score), 2)
    if score >= 82:
        status = "ok"
    elif score >= 64:
        status = "attention"
    else:
        status = "blocker"
    return {
        "id": key,
        "label": label,
        "score": score,
        "status": status,
        "reading": reading,
        "limitation": limitation,
    }


def _headline(score: float, gates: list[dict]) -> str:
    weakest = min(gates, key=lambda item: item["score"], default={"label": "dados", "score": 0})
    if score >= 84:
        return "A carteira tem alta confianca analitica, com criterios claros e pontos de acompanhamento visiveis."
    if score >= 74:
        return f"A carteira esta forte, mas o Alpha ainda quer reforcar {weakest['label'].lower()} para aumentar a confianca."
    if score >= 62:
        return f"A carteira e utilizavel para estudo, porem {weakest['label'].lower()} ainda limita a conviccao."
    return "A carteira exige validacao adicional antes de ser tratada como forte."


def _plain_language(score: float, gates: list[dict], crypto_study: dict | None) -> list[str]:
    weakest = min(gates, key=lambda item: item["score"], default=None)
    strongest = max(gates, key=lambda item: item["score"], default=None)
    lines = [
        f"Hoje a confianca Alpha esta em {score:.0f}/100: boa para leitura, mas nunca e certeza absoluta.",
    ]
    if strongest:
        lines.append(f"O ponto mais forte agora e {strongest['label'].lower()}.")
    if weakest:
        lines.append(f"O ponto que mais limita a confianca e {weakest['label'].lower()}.")
    if crypto_study:
        lines.append(f"A cripto do mes ({crypto_study.get('ticker')}) entra como tese especulativa, nao como nucleo patrimonial.")
    lines.append("Se qualquer dado essencial ficar fraco, o sistema deve reduzir a nota antes de manter a indicacao forte.")
    return lines


def _asset_reading(asset: dict, asset_class: str, score: float, classification: str) -> str:
    ticker = asset.get("ticker")
    role = asset.get("role") or asset.get("conviction") or "papel estrategico"
    if score >= 82:
        return f"{ticker} tem alta confianca Alpha dentro de {asset_class}: {role}."
    if score >= 70:
        return f"{ticker} segue adequado ao estudo, mas precisa continuar sendo acompanhado: {role}."
    return f"{ticker} permanece em {classification.lower()} e exige acompanhamento antes de aumentar exposicao."


def _asset_classification(score: float, risk_level: str | None) -> str:
    if str(risk_level or "").lower() == "extremo":
        return "Especulativa controlada"
    if score >= 84:
        return "Alta confianca Alpha"
    if score >= 74:
        return "Boa confianca Alpha"
    if score >= 62:
        return "Confianca em construcao"
    return "Exige validacao"


def _asset_status(score: float) -> str:
    if score >= 82:
        return "ok"
    if score >= 62:
        return "attention"
    return "blocker"


def _classification(score: float) -> str:
    if score >= 84:
        return "Alta confianca Alpha"
    if score >= 74:
        return "Boa confianca Alpha"
    if score >= 62:
        return "Confianca em construcao"
    return "Exige validacao adicional"


def _b3_data_mode(screener: dict) -> str:
    if screener.get("universeSource") == "brapi_available":
        return "brapi_universe"
    return "foundation_internal_universe"


def _data_score(data_mode: str | None, data_fields: float) -> float:
    if data_mode in {"provider_validated", "brapi_universe", "live"}:
        base = 82
    elif data_mode in {"partial_provider_data", "analisado"}:
        base = 68
    elif data_mode in {"foundation", "foundation_watchlist", "foundation_internal_universe"}:
        base = 58
    else:
        base = 54
    return _clamp(base + min(16, data_fields * 2))


def _allocation_score(weight: float) -> float:
    if weight <= 0:
        return 62
    if weight <= 10:
        return 90
    if weight <= 13:
        return 84
    if weight <= 16:
        return 74
    return 58


def _average(values: list[float]) -> float:
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
