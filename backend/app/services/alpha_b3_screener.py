from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import isfinite
import re

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.asset_engine import ensure_asset_engine_metadata
from app.core.config import get_settings
from app.models import Asset
from app.services.market_data.sync import sync_asset_market_data
from app.services.scoring import dividend_score, risk_score, safety_score, valuation_score


PERENNIAL_CANDIDATES = [
    {
        "ticker": "BBSE3",
        "name": "BB Seguridade",
        "sector": "Seguros",
        "role": "Pilar de renda passiva",
        "quality": 93,
        "liquidity": 92,
        "governance": 86,
        "risk": 28,
        "thesis": "Seguradora de alta rentabilidade, forte geracao de caixa e historico consistente de distribuicao de resultados.",
        "watchpoints": ["Dependencia do Banco do Brasil", "Mudancas regulatorias", "Ciclo de juros"],
    },
    {
        "ticker": "TAEE11",
        "name": "Taesa",
        "sector": "Energia",
        "role": "Previsibilidade de dividendos",
        "quality": 92,
        "liquidity": 82,
        "governance": 82,
        "risk": 30,
        "thesis": "Transmissora de energia com receita regulada, contratos longos e perfil historicamente adequado para dividendos.",
        "watchpoints": ["Revisoes regulatorias", "Vencimento de concessoes", "Custo de capital"],
    },
    {
        "ticker": "ITSA4",
        "name": "Itausa",
        "sector": "Holding financeira",
        "role": "Exposicao financeira defensiva",
        "quality": 90,
        "liquidity": 94,
        "governance": 84,
        "risk": 34,
        "thesis": "Holding com exposicao relevante a Itau, historico de dividendos e diversificacao em negocios resilientes.",
        "watchpoints": ["Desconto de holding", "Dependencia do setor financeiro", "Alocacao de capital"],
    },
    {
        "ticker": "BBAS3",
        "name": "Banco do Brasil",
        "sector": "Bancos",
        "role": "Banco de grande escala",
        "quality": 88,
        "liquidity": 94,
        "governance": 74,
        "risk": 42,
        "thesis": "Banco dominante, rentabilidade alta, forte presenca no agro e capacidade relevante de pagamento de dividendos.",
        "watchpoints": ["Risco de interferencia estatal", "Ciclo de credito", "Inadimplencia"],
    },
    {
        "ticker": "EGIE3",
        "name": "Engie Brasil",
        "sector": "Energia",
        "role": "Qualidade defensiva",
        "quality": 88,
        "liquidity": 82,
        "governance": 88,
        "risk": 34,
        "thesis": "Geradora privada de energia com ativos de qualidade, disciplina financeira e perfil defensivo.",
        "watchpoints": ["Risco hidrologico", "Preco de energia", "Capex de expansao"],
    },
    {
        "ticker": "CPFE3",
        "name": "CPFL Energia",
        "sector": "Energia",
        "role": "Energia integrada",
        "quality": 86,
        "liquidity": 80,
        "governance": 82,
        "risk": 36,
        "thesis": "Companhia integrada de energia com operacao madura, escala e historico de retorno ao acionista.",
        "watchpoints": ["Regulacao", "Distribuicao de energia", "Alavancagem"],
    },
    {
        "ticker": "SAPR11",
        "name": "Sanepar",
        "sector": "Saneamento",
        "role": "Servico essencial",
        "quality": 84,
        "liquidity": 72,
        "governance": 72,
        "risk": 42,
        "thesis": "Saneamento basico com demanda resiliente, concessoes longas e potencial de distribuicao em setor essencial.",
        "watchpoints": ["Risco politico estadual", "Regulacao", "Necessidade de investimento"],
    },
    {
        "ticker": "PSSA3",
        "name": "Porto Seguro",
        "sector": "Seguros",
        "role": "Seguros e resiliencia",
        "quality": 83,
        "liquidity": 76,
        "governance": 82,
        "risk": 38,
        "thesis": "Seguradora privada com marca forte, diversificacao de produtos e perfil defensivo.",
        "watchpoints": ["Sinistralidade", "Concorrencia", "Resultado financeiro"],
    },
    {
        "ticker": "VIVT3",
        "name": "Telefonica Brasil",
        "sector": "Telecom",
        "role": "Caixa defensivo",
        "quality": 82,
        "liquidity": 84,
        "governance": 80,
        "risk": 40,
        "thesis": "Telecom lider com fluxo de caixa recorrente, baixo risco de ruptura e historico de remuneracao ao acionista.",
        "watchpoints": ["Competicao", "Capex de rede", "Crescimento baixo"],
    },
    {
        "ticker": "CSMG3",
        "name": "Copasa",
        "sector": "Saneamento",
        "role": "Saneamento complementar",
        "quality": 80,
        "liquidity": 70,
        "governance": 70,
        "risk": 44,
        "thesis": "Empresa de saneamento em setor essencial, com possibilidade de eficiencia e retorno em renda passiva.",
        "watchpoints": ["Risco politico estadual", "Capex", "Qualidade regulatoria"],
    },
    {
        "ticker": "CPLE6",
        "name": "Copel",
        "sector": "Energia",
        "role": "Energia pos-privatizacao",
        "quality": 79,
        "liquidity": 84,
        "governance": 78,
        "risk": 44,
        "thesis": "Companhia de energia com potencial de eficiencia apos privatizacao e diversificacao de ativos.",
        "watchpoints": ["Execucao pos-privatizacao", "Risco hidrologico", "Regulacao"],
    },
    {
        "ticker": "CXSE3",
        "name": "Caixa Seguridade",
        "sector": "Seguros",
        "role": "Seguros com dividendos",
        "quality": 78,
        "liquidity": 75,
        "governance": 70,
        "risk": 45,
        "thesis": "Seguradora ligada a rede de distribuicao da Caixa, com perfil de renda e margens relevantes.",
        "watchpoints": ["Dependencia da Caixa", "Governanca estatal", "Crescimento"],
    },
    {
        "ticker": "ABCB4",
        "name": "Banco ABC Brasil",
        "sector": "Bancos",
        "role": "Banco medio eficiente",
        "quality": 76,
        "liquidity": 66,
        "governance": 78,
        "risk": 48,
        "thesis": "Banco medio com historico de rentabilidade e nicho corporativo, mas com menor escala que bancos grandes.",
        "watchpoints": ["Liquidez menor", "Ciclo de credito", "Concentracao corporativa"],
    },
    {
        "ticker": "BBDC4",
        "name": "Bradesco",
        "sector": "Bancos",
        "role": "Recuperacao bancaria",
        "quality": 72,
        "liquidity": 96,
        "governance": 82,
        "risk": 55,
        "thesis": "Banco grande com potencial de recuperacao, mas que exige melhora clara de rentabilidade.",
        "watchpoints": ["ROE em recuperacao", "Inadimplencia", "Competicao"],
    },
    {
        "ticker": "CMIG4",
        "name": "Cemig",
        "sector": "Energia",
        "role": "Yield com risco politico",
        "quality": 74,
        "liquidity": 86,
        "governance": 66,
        "risk": 56,
        "thesis": "Empresa de energia com dividendos historicos elevados, mas maior risco politico e regulatorio.",
        "watchpoints": ["Interferencia politica", "Risco hidrologico", "Capex"],
    },
    {
        "ticker": "AURE3",
        "name": "Auren Energia",
        "sector": "Energia",
        "role": "Energia em maturacao",
        "quality": 70,
        "liquidity": 78,
        "governance": 76,
        "risk": 50,
        "thesis": "Energia renovavel com potencial, mas historico mais curto e dividendos menos previsiveis.",
        "watchpoints": ["Maturacao dos ativos", "Risco hidrologico", "Dividendos extraordinarios"],
    },
    {
        "ticker": "BRSR6",
        "name": "Banrisul",
        "sector": "Bancos",
        "role": "Banco regional",
        "quality": 68,
        "liquidity": 66,
        "governance": 60,
        "risk": 58,
        "thesis": "Banco regional com desconto e dividendos, mas risco politico e concentracao geografica maiores.",
        "watchpoints": ["Rio Grande do Sul", "Governanca estatal", "Liquidez"],
    },
]

OFFICIAL_TARGET_WEIGHTS = {
    "BBSE3": 13,
    "TAEE11": 12,
    "ITSA4": 11,
    "BBAS3": 10,
    "EGIE3": 10,
    "CPFE3": 9,
    "SAPR11": 9,
    "PSSA3": 8,
    "VIVT3": 8,
    "CSMG3": 10,
}

SECTOR_STABILITY = {
    "Energia": 92,
    "Saneamento": 90,
    "Seguros": 88,
    "Bancos": 82,
    "Holding financeira": 82,
    "Telecom": 76,
}


def run_alpha_b3_screener(db: Session | None = None, *, refresh_market: bool = False) -> dict:
    if db is None:
        raw_universe, universe_source = ([item["ticker"] for item in PERENNIAL_CANDIDATES], "fallback_internal_universe")
    else:
        raw_universe, universe_source = _fetch_b3_universe()
    eligible_universe = [ticker for ticker in raw_universe if _is_probable_equity(ticker)]
    candidate_rows = []

    for candidate in PERENNIAL_CANDIDATES:
        asset = _ensure_candidate_asset(db, candidate) if db is not None else None
        if db is not None and asset is not None and refresh_market:
            try:
                sync_asset_market_data(db, asset)
            except Exception:
                pass
        snapshot = asset.snapshot if asset is not None else None
        row = _score_candidate(candidate, snapshot)
        row["inBrapiUniverse"] = candidate["ticker"] in eligible_universe or not raw_universe
        candidate_rows.append(row)

    ranking = sorted(candidate_rows, key=lambda item: item["alphaScore"], reverse=True)
    selected_by_ticker = {row["ticker"]: row for row in ranking if row["ticker"] in OFFICIAL_TARGET_WEIGHTS}
    portfolio = []
    for ticker, weight in OFFICIAL_TARGET_WEIGHTS.items():
        row = selected_by_ticker[ticker]
        portfolio.append(
            {
                "ticker": row["ticker"],
                "name": row["name"],
                "sector": row["sector"],
                "class": "Acoes",
                "targetWeight": weight,
                "riskLevel": row["riskLevel"],
                "role": row["role"],
                "alphaScore": row["alphaScore"],
                "alphaReading": row["alphaReading"],
                "thesis": row["thesis"],
                "watchpoints": row["watchpoints"],
                "whySelected": row["whySelected"],
                "dataFields": row["dataFields"],
            }
        )

    sector_allocation: dict[str, float] = {}
    for asset in portfolio:
        sector_allocation[asset["sector"]] = sector_allocation.get(asset["sector"], 0) + float(asset["targetWeight"])

    if db is not None and refresh_market:
        db.commit()

    return {
        "id": "screener-alpha-b3-dividendos-2026-07-11",
        "title": "Screener Alpha B3",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "universeSource": universe_source,
        "rawUniverseCount": len(raw_universe),
        "eligibleUniverseCount": len(eligible_universe),
        "candidateCount": len(candidate_rows),
        "selectedCount": len(portfolio),
        "strategy": "Dividendos, setores perenes, qualidade financeira e risco controlado.",
        "filters": [
            "Bolsa brasileira B3.",
            "Remocao de FIIs, ETFs, BDRs, recibos, fracionarios e tickers sem perfil de acao local.",
            "Foco em setores essenciais: energia, saneamento, bancos, seguros, holding financeira e telecom.",
            "Priorizacao de dividendos, caixa recorrente, qualidade, liquidez e perenidade.",
            "Penalizacao de risco politico, alavancagem, baixa previsibilidade e baixa liquidez.",
        ],
        "portfolio": portfolio,
        "ranking": ranking,
        "sectorAllocation": [{"name": name, "value": value} for name, value in sorted(sector_allocation.items())],
        "excludedHighlights": [
            _excluded("BBDC4", "Banco grande, mas ficou fora do nucleo por ainda depender de recuperacao de rentabilidade."),
            _excluded("BRSR6", "Banco regional com desconto, mas maior risco politico e concentracao geografica."),
            _excluded("AURE3", "Boa candidata de energia, mas a previsibilidade de dividendos ainda e menor que as selecionadas."),
            _excluded("CPLE6", "Boa empresa de energia, mas perdeu vaga para CPFE3/EGIE3/TAEE11 na composicao atual."),
        ],
    }


def _score_candidate(candidate: dict, snapshot) -> dict:
    data_fields = _snapshot_fields(snapshot)
    if snapshot is not None:
        dividend, dividend_reasons = dividend_score(snapshot)
        safety = safety_score(snapshot)
        valuation = valuation_score(snapshot)
        quantitative_risk = risk_score(snapshot)
    else:
        dividend = safety = valuation = 0
        quantitative_risk = 55
        dividend_reasons = ["Dados quantitativos ainda nao carregados para este ativo."]

    strategic_score = (
        candidate["quality"] * 0.30
        + candidate["liquidity"] * 0.16
        + candidate["governance"] * 0.16
        + SECTOR_STABILITY.get(candidate["sector"], 65) * 0.20
        + (100 - candidate["risk"]) * 0.18
    )
    if data_fields >= 12:
        data_score = dividend * 0.25 + safety * 0.25 + valuation * 0.18 + (100 - quantitative_risk) * 0.12 + strategic_score * 0.20
    else:
        data_score = strategic_score * 0.86 + min(12, data_fields * 2.5)
    alpha_score = round(_clamp(data_score), 2)
    risk_level = "baixo" if alpha_score >= 86 else "moderado" if alpha_score >= 76 else "controlado" if alpha_score >= 68 else "alto"
    return {
        "ticker": candidate["ticker"],
        "name": candidate["name"],
        "sector": candidate["sector"],
        "role": candidate["role"],
        "alphaScore": alpha_score,
        "riskLevel": risk_level,
        "dataFields": data_fields,
        "scores": {
            "dividends": round(dividend, 2),
            "safety": round(safety, 2),
            "valuation": round(valuation, 2),
            "risk": round(quantitative_risk, 2),
            "strategic": round(strategic_score, 2),
        },
        "alphaReading": _alpha_reading(candidate, alpha_score),
        "thesis": candidate["thesis"],
        "watchpoints": candidate["watchpoints"],
        "whySelected": _why_selected(candidate, dividend_reasons),
    }


def _fetch_b3_universe() -> tuple[list[str], str]:
    settings = get_settings()
    params = {}
    if settings.brapi_token:
        params["token"] = settings.brapi_token
    try:
        with httpx.Client(timeout=12) as client:
            response = client.get("https://brapi.dev/api/available", params=params)
            response.raise_for_status()
            payload = response.json()
        stocks = payload.get("stocks") or []
        return [str(ticker).upper() for ticker in stocks if isinstance(ticker, str)], "brapi_available"
    except Exception:
        return [item["ticker"] for item in PERENNIAL_CANDIDATES], "fallback_internal_universe"


def _is_probable_equity(ticker: str) -> bool:
    if not re.fullmatch(r"[A-Z]{4}\d{1,2}", ticker):
        return False
    if ticker.endswith("F"):
        return False
    if ticker.endswith(("31", "32", "33", "34", "35", "39")):
        return False
    if ticker.endswith("11") and ticker not in {"TAEE11", "ALUP11", "ENGI11", "SAPR11", "SANB11", "BPAC11", "KLBN11"}:
        return False
    return True


def _ensure_candidate_asset(db: Session, candidate: dict) -> Asset:
    asset = db.execute(select(Asset).where(Asset.ticker == candidate["ticker"])).scalar_one_or_none()
    if asset is not None:
        return asset
    asset = Asset(
        ticker=candidate["ticker"],
        name=candidate["name"],
        asset_class="Acoes",
        sector=candidate["sector"],
        segment="Screener Alpha B3",
        currency="BRL",
        provider_symbol=candidate["ticker"],
        last_price=Decimal("0"),
    )
    ensure_asset_engine_metadata(db, asset, force=True)
    db.add(asset)
    db.flush()
    return asset


def _snapshot_fields(snapshot) -> int:
    if snapshot is None:
        return 0
    values = [
        snapshot.price,
        snapshot.dividend_yield,
        snapshot.payout,
        snapshot.revenue_growth,
        snapshot.profit_growth,
        snapshot.net_margin,
        snapshot.roe,
        snapshot.roic,
        snapshot.debt_to_ebitda,
        snapshot.pe_ratio,
        snapshot.pvp,
        snapshot.dividend_consistency,
        snapshot.recurring_profit,
        snapshot.sector_stability,
    ]
    return sum(1 for value in values if _to_float(value) != 0)


def _alpha_reading(candidate: dict, alpha_score: float) -> str:
    if alpha_score >= 86:
        label = "Nucleo Alpha"
    elif alpha_score >= 78:
        label = "Alta conviccao"
    elif alpha_score >= 70:
        label = "Compoe a carteira"
    else:
        label = "Peso controlado"
    return f"{label}: {candidate['ticker']} entra pela combinacao de {candidate['role'].lower()}, setor perene e qualidade relativa."


def _why_selected(candidate: dict, dividend_reasons: list[str]) -> list[str]:
    reasons = [
        f"Setor {candidate['sector']} possui demanda estrutural e papel defensivo na carteira.",
        candidate["thesis"],
    ]
    reasons.extend(dividend_reasons[:1])
    return reasons


def _excluded(ticker: str, reason: str) -> dict:
    return {"ticker": ticker, "reason": reason}


def _to_float(value) -> float:
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0
    except Exception:
        return 0


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))
