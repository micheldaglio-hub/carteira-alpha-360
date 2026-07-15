from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import isfinite

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.asset_engine import ensure_asset_engine_metadata
from app.models import Asset
from app.services.market_data.v2.contracts import DATA_TYPE_FUNDAMENTALS, DATA_TYPE_QUOTE, MarketDataRequest
from app.services.market_data.v2.engine import MarketDataEngine


GLOBAL_EQUITY_CANDIDATES = [
    {
        "ticker": "MSFT",
        "name": "Microsoft",
        "country": "Estados Unidos",
        "region": "America do Norte",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Tecnologia",
        "role": "Software, nuvem e IA",
        "quality": 96,
        "moat": 96,
        "liquidity": 98,
        "governance": 90,
        "geographicDiversification": 92,
        "risk": 28,
        "thesis": "Empresa global de software, nuvem e inteligencia artificial, com caixa forte, escala mundial e receitas recorrentes.",
        "watchpoints": ["Valuation elevado", "Concorrencia em IA e nuvem", "Regulacao antitruste"],
    },
    {
        "ticker": "AAPL",
        "name": "Apple",
        "country": "Estados Unidos",
        "region": "America do Norte",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Tecnologia",
        "role": "Ecossistema premium",
        "quality": 94,
        "moat": 95,
        "liquidity": 98,
        "governance": 88,
        "geographicDiversification": 90,
        "risk": 30,
        "thesis": "Marca global, ecossistema forte, fidelidade de clientes e enorme geracao de caixa.",
        "watchpoints": ["Dependencia do iPhone", "China", "Valuation"],
    },
    {
        "ticker": "GOOGL",
        "name": "Alphabet",
        "country": "Estados Unidos",
        "region": "America do Norte",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Tecnologia",
        "role": "Busca, publicidade e IA",
        "quality": 92,
        "moat": 93,
        "liquidity": 96,
        "governance": 82,
        "geographicDiversification": 90,
        "risk": 34,
        "thesis": "Domina busca digital e publicidade, possui infraestrutura relevante de nuvem e forte opcionalidade em IA.",
        "watchpoints": ["Regulacao", "Mudancas em busca por IA", "Ciclos de publicidade"],
    },
    {
        "ticker": "NVDA",
        "name": "NVIDIA",
        "country": "Estados Unidos",
        "region": "America do Norte",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Semicondutores",
        "role": "Infraestrutura de IA",
        "quality": 91,
        "moat": 92,
        "liquidity": 97,
        "governance": 84,
        "geographicDiversification": 88,
        "risk": 48,
        "thesis": "Lider em chips de IA e aceleradores, com grande vantagem competitiva em hardware, software e ecossistema.",
        "watchpoints": ["Valuation muito sensivel", "Ciclo de semicondutores", "Restricoes geopoliticas"],
    },
    {
        "ticker": "V",
        "name": "Visa",
        "country": "Estados Unidos",
        "region": "America do Norte",
        "exchange": "NYSE",
        "currency": "USD",
        "sector": "Pagamentos",
        "role": "Infraestrutura financeira global",
        "quality": 92,
        "moat": 93,
        "liquidity": 94,
        "governance": 88,
        "geographicDiversification": 91,
        "risk": 30,
        "thesis": "Rede global de pagamentos com margens altas, escala e baixa necessidade relativa de capital.",
        "watchpoints": ["Regulacao de taxas", "Competicao fintech", "Ciclos de consumo"],
    },
    {
        "ticker": "JNJ",
        "name": "Johnson & Johnson",
        "country": "Estados Unidos",
        "region": "America do Norte",
        "exchange": "NYSE",
        "currency": "USD",
        "sector": "Saude",
        "role": "Defensivo global",
        "quality": 88,
        "moat": 86,
        "liquidity": 92,
        "governance": 86,
        "geographicDiversification": 88,
        "risk": 34,
        "thesis": "Saude global, historico defensivo e diversificacao em medicamentos e tecnologia medica.",
        "watchpoints": ["Litigios", "Pipeline de medicamentos", "Crescimento moderado"],
    },
    {
        "ticker": "PG",
        "name": "Procter & Gamble",
        "country": "Estados Unidos",
        "region": "America do Norte",
        "exchange": "NYSE",
        "currency": "USD",
        "sector": "Consumo defensivo",
        "role": "Marcas essenciais",
        "quality": 90,
        "moat": 89,
        "liquidity": 92,
        "governance": 88,
        "geographicDiversification": 88,
        "risk": 28,
        "thesis": "Marcas globais de consumo essencial, fluxo de caixa resiliente e perfil defensivo.",
        "watchpoints": ["Cambio", "Margens", "Crescimento baixo"],
    },
    {
        "ticker": "KO",
        "name": "Coca-Cola",
        "country": "Estados Unidos",
        "region": "America do Norte",
        "exchange": "NYSE",
        "currency": "USD",
        "sector": "Consumo defensivo",
        "role": "Marca global e dividendos",
        "quality": 88,
        "moat": 91,
        "liquidity": 92,
        "governance": 86,
        "geographicDiversification": 92,
        "risk": 30,
        "thesis": "Marca global, distribuicao mundial e historico longo de remuneracao ao acionista.",
        "watchpoints": ["Crescimento moderado", "Mudanca de habitos", "Valuation"],
    },
    {
        "ticker": "ASML",
        "name": "ASML Holding",
        "country": "Holanda",
        "region": "Europa",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Semicondutores",
        "role": "Equipamentos criticos",
        "quality": 94,
        "moat": 97,
        "liquidity": 88,
        "governance": 88,
        "geographicDiversification": 86,
        "risk": 42,
        "thesis": "Empresa critica para a cadeia global de semicondutores, com tecnologia dificil de replicar.",
        "watchpoints": ["Geopolitica", "Ciclo de chips", "Restricoes de exportacao"],
    },
    {
        "ticker": "NVO",
        "name": "Novo Nordisk",
        "country": "Dinamarca",
        "region": "Europa",
        "exchange": "NYSE",
        "currency": "USD",
        "sector": "Saude",
        "role": "Medicamentos globais",
        "quality": 93,
        "moat": 91,
        "liquidity": 88,
        "governance": 88,
        "geographicDiversification": 86,
        "risk": 38,
        "thesis": "Lider global em diabetes e obesidade, com forte crescimento e posicionamento em saude.",
        "watchpoints": ["Concorrencia em GLP-1", "Preco de medicamentos", "Valuation"],
    },
    {
        "ticker": "NESN.SW",
        "name": "Nestle",
        "country": "Suica",
        "region": "Europa",
        "exchange": "SIX",
        "currency": "CHF",
        "sector": "Consumo defensivo",
        "role": "Consumo global defensivo",
        "quality": 87,
        "moat": 88,
        "liquidity": 78,
        "governance": 86,
        "geographicDiversification": 94,
        "risk": 30,
        "thesis": "Empresa global de alimentos e bebidas, marcas fortes e exposicao ampla a mercados desenvolvidos e emergentes.",
        "watchpoints": ["Cambio", "Crescimento baixo", "Margens"],
    },
    {
        "ticker": "TSM",
        "name": "Taiwan Semiconductor",
        "country": "Taiwan",
        "region": "Asia",
        "exchange": "NYSE",
        "currency": "USD",
        "sector": "Semicondutores",
        "role": "Foundry global",
        "quality": 93,
        "moat": 94,
        "liquidity": 92,
        "governance": 84,
        "geographicDiversification": 82,
        "risk": 50,
        "thesis": "Principal fabricante terceirizada de chips avancados, essencial para tecnologia global.",
        "watchpoints": ["Risco geopolitico Taiwan-China", "Ciclo de semicondutores", "Capex elevado"],
    },
    {
        "ticker": "BHP",
        "name": "BHP Group",
        "country": "Australia",
        "region": "Oceania",
        "exchange": "NYSE",
        "currency": "USD",
        "sector": "Materiais",
        "role": "Commodities globais",
        "quality": 82,
        "moat": 78,
        "liquidity": 86,
        "governance": 82,
        "geographicDiversification": 78,
        "risk": 52,
        "thesis": "Mineradora global com exposicao a commodities estruturais, diversificando a carteira para economia real.",
        "watchpoints": ["Ciclo de commodities", "China", "Volatilidade de minerio e cobre"],
    },
]

GLOBAL_TARGET_WEIGHTS = {
    "MSFT": 11,
    "AAPL": 8,
    "GOOGL": 8,
    "NVDA": 7,
    "V": 7,
    "JNJ": 7,
    "PG": 7,
    "KO": 6,
    "ASML": 8,
    "NVO": 7,
    "NESN.SW": 7,
    "TSM": 8,
    "BHP": 9,
}


def run_alpha_global_equity_screener(db: Session | None = None, *, refresh_market: bool = False) -> dict:
    market_engine = MarketDataEngine(db=db) if db is not None and refresh_market else None
    rows = []
    for candidate in GLOBAL_EQUITY_CANDIDATES:
        asset = _ensure_global_asset(db, candidate) if db is not None else None
        evidence = _collect_evidence(market_engine, candidate, asset.id if asset else None) if market_engine else {}
        rows.append(_score_candidate(candidate, evidence))

    ranking = sorted(rows, key=lambda item: item["alphaScore"], reverse=True)
    by_ticker = {row["ticker"]: row for row in ranking}
    portfolio = [{**by_ticker[ticker], "targetWeight": weight, "class": "Global Equity"} for ticker, weight in GLOBAL_TARGET_WEIGHTS.items()]

    region_allocation: dict[str, float] = {}
    currency_allocation: dict[str, float] = {}
    sector_allocation: dict[str, float] = {}
    for item in portfolio:
        region_allocation[item["region"]] = region_allocation.get(item["region"], 0) + float(item["targetWeight"])
        currency_allocation[item["currency"]] = currency_allocation.get(item["currency"], 0) + float(item["targetWeight"])
        sector_allocation[item["sector"]] = sector_allocation.get(item["sector"], 0) + float(item["targetWeight"])

    if db is not None and refresh_market:
        db.commit()

    return {
        "id": "screener-alpha-global-equities-2026-07-12",
        "title": "Screener Alpha Global",
        "status": "foundation_ready",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "strategy": "Acoes internacionais de qualidade, diversificacao geografica, moedas fortes, setores globais e risco controlado.",
        "candidateCount": len(rows),
        "selectedCount": len(portfolio),
        "dataMode": "provider_validated" if refresh_market else "foundation_watchlist",
        "filters": [
            "Nao concentrar patrimonio apenas no Brasil.",
            "Priorizar empresas globais com vantagem competitiva, liquidez, governanca e escala internacional.",
            "Diversificar por pais, moeda, setor e regiao.",
            "Usar FMP e Twelve Data para fundamentos, precos, dividendos e historicos quando as chaves estiverem configuradas.",
            "Nao tratar a lista como garantia de retorno nem como promessa de que um especialista externo concordaria.",
        ],
        "portfolio": portfolio,
        "ranking": ranking,
        "regionAllocation": _allocation_rows(region_allocation),
        "currencyAllocation": _allocation_rows(currency_allocation),
        "sectorAllocation": _allocation_rows(sector_allocation),
        "validationNote": (
            "Esta e a fundacao do screener global. A selecao combina criterios estruturais Alpha e pode ser enriquecida por FMP/Twelve Data "
            "ao atualizar a analise. Ainda nao representa backtest completo de todas as bolsas do mundo."
        ),
        "nextSteps": [
            "Persistir rodadas mensais do screener global.",
            "Adicionar backtest internacional com cambio USD/BRL.",
            "Criar mapa por pais, moeda e bolsa.",
            "Comparar stocks, BDRs e ETFs internacionais para execucao pratica.",
        ],
    }


def _score_candidate(candidate: dict, evidence: dict) -> dict:
    strategic_score = (
        candidate["quality"] * 0.25
        + candidate["moat"] * 0.22
        + candidate["liquidity"] * 0.14
        + candidate["governance"] * 0.13
        + candidate["geographicDiversification"] * 0.14
        + (100 - candidate["risk"]) * 0.12
    )
    fundamentals = evidence.get("fundamentals") or {}
    data_score, data_fields = _fundamental_score(fundamentals)
    if data_fields >= 4:
        alpha_score = strategic_score * 0.62 + data_score * 0.38
        data_status = "provider_validated"
    elif data_fields:
        alpha_score = strategic_score * 0.82 + data_score * 0.18
        data_status = "partial_provider_data"
    else:
        alpha_score = strategic_score
        data_status = "foundation"

    alpha_score = round(_clamp(alpha_score), 2)
    if alpha_score >= 88:
        conviction = "Nucleo global"
    elif alpha_score >= 82:
        conviction = "Alta qualidade global"
    elif alpha_score >= 76:
        conviction = "Compoe diversificacao"
    else:
        conviction = "Peso controlado"

    return {
        "ticker": candidate["ticker"],
        "name": candidate["name"],
        "country": candidate["country"],
        "region": candidate["region"],
        "exchange": candidate["exchange"],
        "currency": candidate["currency"],
        "sector": candidate["sector"],
        "role": candidate["role"],
        "alphaScore": alpha_score,
        "conviction": conviction,
        "riskLevel": "moderado" if candidate["risk"] < 40 else "moderado_alto" if candidate["risk"] < 50 else "alto_controlado",
        "dataStatus": data_status,
        "dataFields": data_fields,
        "price": round(_to_float(evidence.get("price")), 4),
        "scores": {
            "strategic": round(strategic_score, 2),
            "fundamentals": round(data_score, 2),
            "quality": candidate["quality"],
            "moat": candidate["moat"],
            "liquidity": candidate["liquidity"],
            "risk": candidate["risk"],
        },
        "alphaReading": f"{conviction}: {candidate['ticker']} entra por qualidade, vantagem competitiva, liquidez e diversificacao internacional.",
        "thesis": candidate["thesis"],
        "watchpoints": candidate["watchpoints"],
        "whySelected": [
            f"Exposicao a {candidate['country']} / {candidate['region']} em moeda {candidate['currency']}.",
            candidate["thesis"],
            "Ajuda a reduzir dependencia estrutural do Brasil quando combinada com controle de cambio e peso.",
        ],
    }


def _fundamental_score(payload: dict) -> tuple[float, int]:
    if not payload:
        return 0.0, 0
    roe = _to_float(payload.get("roe"))
    margin = _to_float(payload.get("net_margin"))
    revenue_growth = _to_float(payload.get("revenue_growth"))
    profit_growth = _to_float(payload.get("profit_growth"))
    dividend_yield = _to_float(payload.get("dividend_yield"))
    pe = _to_float(payload.get("pe_ratio"))
    pvp = _to_float(payload.get("pvp"))
    fields = sum(1 for value in [roe, margin, revenue_growth, profit_growth, dividend_yield, pe, pvp] if value != 0)
    score = (
        _band(roe, 8, 32) * 0.22
        + _band(margin, 8, 38) * 0.18
        + _band(revenue_growth, -4, 24) * 0.16
        + _band(profit_growth, -6, 30) * 0.16
        + _band(dividend_yield, 0, 4) * 0.08
        + _inverse_band(abs(pe - 24), 0, 45) * 0.12
        + _inverse_band(abs(pvp - 6), 0, 18) * 0.08
    )
    return round(_clamp(score), 2), fields


def _collect_evidence(engine: MarketDataEngine, candidate: dict, asset_id: str | None) -> dict:
    request = MarketDataRequest(
        symbol=candidate["ticker"],
        asset_id=asset_id,
        market=candidate["exchange"],
        asset_class="Acoes",
        currency=candidate["currency"],
    )
    evidence: dict = {}
    try:
        quotes = engine.collect(DATA_TYPE_QUOTE, request, include_mock=False)
        best_quote = max(quotes, key=lambda item: item.quality_score, default=None)
        if best_quote:
            evidence["price"] = best_quote.payload.get("price")
            evidence["quoteProvider"] = best_quote.provider
    except Exception:
        pass
    try:
        fundamentals = engine.collect(DATA_TYPE_FUNDAMENTALS, request, include_mock=False)
        best = max(fundamentals, key=lambda item: item.quality_score, default=None)
        if best:
            evidence["fundamentals"] = best.payload
            evidence["fundamentalsProvider"] = best.provider
    except Exception:
        pass
    return evidence


def _ensure_global_asset(db: Session | None, candidate: dict) -> Asset | None:
    if db is None:
        return None
    asset = db.execute(select(Asset).where(Asset.ticker == candidate["ticker"])).scalar_one_or_none()
    if asset is not None:
        return asset
    asset = Asset(
        ticker=candidate["ticker"],
        name=candidate["name"],
        asset_class="Acoes",
        asset_subclass="Global Equity",
        sector=candidate["sector"],
        segment="Screener Alpha Global",
        currency=candidate["currency"],
        base_currency=candidate["currency"],
        trading_currency=candidate["currency"],
        region=candidate["region"],
        market=candidate["exchange"],
        exchange=candidate["exchange"],
        provider_symbol=candidate["ticker"],
        last_price=Decimal("0"),
    )
    ensure_asset_engine_metadata(db, asset, force=True)
    db.add(asset)
    db.flush()
    return asset


def _allocation_rows(source: dict[str, float]) -> list[dict]:
    return [{"name": name, "value": value} for name, value in sorted(source.items(), key=lambda item: item[0])]


def _to_float(value) -> float:
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0
    except Exception:
        return 0


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def _band(value: float, low: float, high: float) -> float:
    if high == low:
        return 0
    return _clamp((value - low) / (high - low) * 100)


def _inverse_band(value: float, low: float, high: float) -> float:
    return 100 - _band(value, low, high)
