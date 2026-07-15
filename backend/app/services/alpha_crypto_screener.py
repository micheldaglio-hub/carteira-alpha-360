from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from math import isfinite
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import UserPreference
from app.services.crypto_research_engine import CryptoResearchEngine
from app.services.portfolio import get_positions


SCREENER_CACHE_PREFIX = "alpha_crypto_screener"
STABLE_OR_NON_SPECULATIVE = {"USDT", "USDC", "FDUSD", "TUSD", "DAI", "BUSD", "EUR", "BRL", "PAXG"}
BLOCKED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")

NARRATIVES: dict[str, dict[str, Any]] = {
    "JASMY": {
        "name": "JasmyCoin",
        "themes": ["IoT", "soberania de dados", "Japao"],
        "score": 16,
        "thesis": "baixo preco unitario, Binance Spot e narrativa de IoT/soberania de dados.",
    },
    "IOTX": {"name": "IoTeX", "themes": ["DePIN", "IoT"], "score": 15, "thesis": "infraestrutura DePIN/IoT com tese de dispositivos conectados."},
    "FET": {"name": "Fetch.ai", "themes": ["IA", "agentes autonomos"], "score": 16, "thesis": "exposicao a narrativa de IA cripto e agentes autonomos."},
    "GRT": {"name": "The Graph", "themes": ["dados", "indexacao"], "score": 14, "thesis": "infraestrutura de dados e indexacao para ecossistemas blockchain."},
    "ROSE": {"name": "Oasis", "themes": ["privacidade", "dados"], "score": 14, "thesis": "privacidade e dados confidenciais em blockchain."},
    "VET": {"name": "VeChain", "themes": ["supply chain", "enterprise"], "score": 13, "thesis": "rastreabilidade, supply chain e uso empresarial."},
    "COTI": {"name": "COTI", "themes": ["pagamentos", "infraestrutura"], "score": 12, "thesis": "pagamentos e infraestrutura financeira cripto."},
    "GALA": {"name": "Gala", "themes": ["games", "entretenimento"], "score": 10, "thesis": "games e entretenimento, com risco alto de ciclo narrativo."},
    "HBAR": {"name": "Hedera", "themes": ["enterprise", "infraestrutura"], "score": 12, "thesis": "rede enterprise com governanca corporativa e alto reconhecimento."},
    "ADA": {"name": "Cardano", "themes": ["smart contracts", "ecossistema"], "score": 9, "thesis": "projeto grande e liquido, mas com menor assimetria por market cap maior."},
    "XLM": {"name": "Stellar", "themes": ["pagamentos", "remessas"], "score": 9, "thesis": "pagamentos/remessas com alta liquidez, menor perfil de moonshot."},
}

FALLBACK_CANDIDATE = {
    "ticker": "JASMY",
    "name": "JasmyCoin",
    "priceUsd": 0.0,
    "marketCapUsd": 0.0,
    "volumeUsd": 0.0,
    "priceChange24hPct": 0.0,
    "priceChange7dPct": 0.0,
    "priceChange30dPct": 0.0,
    "binancePairs": ["JASMY/USDT"],
    "alphaScore": 78.0,
    "selectionReason": "Candidata fallback: acessivel na Binance Spot e alinhada ao estudo JASMY importado.",
    "decisionType": "nova_oportunidade",
    "source": "fallback",
}


@dataclass
class MarketCandidate:
    ticker: str
    name: str
    price_usd: float
    market_cap_usd: float
    volume_usd: float
    price_change_24h_pct: float
    price_change_7d_pct: float
    price_change_30d_pct: float
    binance_pairs: list[str]
    source: str


def run_alpha_crypto_screener(
    db: Session | None = None,
    user_id: str | None = None,
    *,
    refresh_market: bool = False,
    today: date | None = None,
) -> dict:
    """Run the monthly opportunity scanner.

    The engine searches the external market first. Existing user holdings are used only after ranking,
    to decide whether the monthly action is a new opportunity study or a reinforcement of a thesis already held.
    """

    current_date = today or date.today()
    cache_key = f"{SCREENER_CACHE_PREFIX}:{current_date:%Y-%m}"
    if db is not None and user_id and not refresh_market:
        cached = _load_cache(db, user_id, cache_key)
        if cached:
            return cached

    holdings = _current_crypto_context(db, user_id) if db is not None and user_id else {}
    candidates = []
    if db is not None or refresh_market:
        try:
            candidates = _fetch_live_candidates()
        except Exception:
            candidates = []

    ranking = _rank_candidates(candidates, holdings)
    if not ranking:
        ranking = [_fallback_candidate(holdings)]

    research = CryptoResearchEngine().research_candidates(ranking, holdings)
    selected_report = research.get("selected")
    selected = _candidate_from_research(selected_report, ranking[0]) if selected_report else ranking[0]
    payload = _build_payload(selected, ranking, holdings, current_date, live=bool(candidates), research=research)

    if db is not None and user_id:
        _save_cache(db, user_id, cache_key, payload)
    return payload


def _fetch_live_candidates() -> list[MarketCandidate]:
    binance = _fetch_binance_universe()
    market_rows = _fetch_coinmarketcap_rows() or _fetch_coingecko_rows()
    rows_by_symbol = {}
    for row in market_rows:
        symbol = str(row.get("symbol") or "").upper().strip()
        if symbol and symbol not in rows_by_symbol:
            rows_by_symbol[symbol] = row

    candidates: list[MarketCandidate] = []
    for symbol, access in binance.items():
        if not _is_candidate_symbol(symbol):
            continue
        row = rows_by_symbol.get(symbol, {})
        ticker = access["baseAsset"]
        price = _first_number(access.get("lastPrice"), row.get("priceUsd"), row.get("price"))
        market_cap = _first_number(row.get("marketCapUsd"), row.get("market_cap"), row.get("marketCap"))
        volume = _first_number(access.get("quoteVolume"), row.get("volumeUsd"), row.get("total_volume"), row.get("volume24h"))
        if price <= 0 or volume <= 0:
            continue
        if price > 2:
            continue
        candidates.append(
            MarketCandidate(
                ticker=ticker,
                name=str(row.get("name") or NARRATIVES.get(ticker, {}).get("name") or ticker),
                price_usd=price,
                market_cap_usd=market_cap,
                volume_usd=volume,
                price_change_24h_pct=_first_number(access.get("priceChangePercent"), row.get("priceChange24hPct"), row.get("percent_change_24h")),
                price_change_7d_pct=_first_number(row.get("priceChange7dPct"), row.get("price_change_percentage_7d_in_currency"), row.get("percent_change_7d")),
                price_change_30d_pct=_first_number(row.get("priceChange30dPct"), row.get("price_change_percentage_30d_in_currency"), row.get("percent_change_30d")),
                binance_pairs=access["pairs"],
                source=str(row.get("source") or "binance"),
            )
        )
    return candidates


def _fetch_binance_universe() -> dict[str, dict]:
    with httpx.Client(timeout=12.0) as client:
        exchange = client.get("https://api.binance.com/api/v3/exchangeInfo").json()
        tickers = client.get("https://api.binance.com/api/v3/ticker/24hr").json()

    ticker_by_symbol = {row.get("symbol"): row for row in tickers if isinstance(row, dict)}
    universe: dict[str, dict] = {}
    for symbol in exchange.get("symbols", []):
        if not isinstance(symbol, dict):
            continue
        if symbol.get("status") != "TRADING" or symbol.get("quoteAsset") != "USDT" or not symbol.get("isSpotTradingAllowed"):
            continue
        base = str(symbol.get("baseAsset") or "").upper()
        pair = str(symbol.get("symbol") or "")
        ticker = ticker_by_symbol.get(pair, {})
        universe[base] = {
            "baseAsset": base,
            "pairs": [f"{base}/USDT"],
            "lastPrice": ticker.get("lastPrice"),
            "quoteVolume": ticker.get("quoteVolume"),
            "priceChangePercent": ticker.get("priceChangePercent"),
        }
    return universe


def _fetch_coinmarketcap_rows() -> list[dict]:
    settings = get_settings()
    if not settings.coinmarketcap_api_key:
        return []
    headers = {"X-CMC_PRO_API_KEY": settings.coinmarketcap_api_key, "Accept": "application/json"}
    params = {"start": 1, "limit": 1000, "convert": "USD", "sort": "market_cap", "sort_dir": "desc"}
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest", headers=headers, params=params)
            response.raise_for_status()
            rows = response.json().get("data") or []
    except Exception:
        return []
    normalized = []
    for row in rows:
        quote = ((row.get("quote") or {}).get("USD") or {}) if isinstance(row, dict) else {}
        normalized.append(
            {
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "priceUsd": quote.get("price"),
                "marketCapUsd": quote.get("market_cap"),
                "volumeUsd": quote.get("volume_24h"),
                "priceChange24hPct": quote.get("percent_change_24h"),
                "priceChange7dPct": quote.get("percent_change_7d"),
                "priceChange30dPct": quote.get("percent_change_30d"),
                "source": "coinmarketcap",
            }
        )
    return normalized


def _fetch_coingecko_rows() -> list[dict]:
    settings = get_settings()
    headers = {"Accept": "application/json"}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key
    rows: list[dict] = []
    with httpx.Client(timeout=12.0) as client:
        for page in range(1, 5):
            response = client.get(
                f"{settings.coingecko_base_url.rstrip('/')}/coins/markets",
                headers=headers,
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 250,
                    "page": page,
                    "sparkline": "false",
                    "price_change_percentage": "7d,30d",
                },
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                break
            rows.extend(data)
    normalized = []
    for row in rows:
        normalized.append(
            {
                "symbol": str(row.get("symbol") or "").upper(),
                "name": row.get("name"),
                "priceUsd": row.get("current_price"),
                "marketCapUsd": row.get("market_cap"),
                "volumeUsd": row.get("total_volume"),
                "priceChange24hPct": row.get("price_change_percentage_24h"),
                "priceChange7dPct": row.get("price_change_percentage_7d_in_currency"),
                "priceChange30dPct": row.get("price_change_percentage_30d_in_currency"),
                "source": "coingecko",
            }
        )
    return normalized


def _rank_candidates(candidates: list[MarketCandidate], holdings: dict[str, dict]) -> list[dict]:
    ranked = []
    for candidate in candidates:
        score, parts = _score_candidate(candidate, holdings)
        if score < 45:
            continue
        holding = holdings.get(candidate.ticker)
        decision_type = "reforcar_tese_existente" if holding else "nova_oportunidade"
        ranked.append(
            {
                "ticker": candidate.ticker,
                "name": candidate.name,
                "priceUsd": round(candidate.price_usd, 8),
                "marketCapUsd": round(candidate.market_cap_usd, 2),
                "volumeUsd": round(candidate.volume_usd, 2),
                "priceChange24hPct": round(candidate.price_change_24h_pct, 2),
                "priceChange7dPct": round(candidate.price_change_7d_pct, 2),
                "priceChange30dPct": round(candidate.price_change_30d_pct, 2),
                "binancePairs": candidate.binance_pairs,
                "alphaScore": round(score, 2),
                "scoreBreakdown": parts,
                "decisionType": decision_type,
                "alreadyInPortfolio": bool(holding),
                "currentPortfolioValue": round(_float((holding or {}).get("currentValue")), 2),
                "portfolioReturnPct": round(_float((holding or {}).get("returnPct")), 2),
                "selectionReason": _selection_reason(candidate, holding),
                "source": candidate.source,
            }
        )
    return sorted(ranked, key=lambda item: item["alphaScore"], reverse=True)[:12]


def _score_candidate(candidate: MarketCandidate, holdings: dict[str, dict]) -> tuple[float, dict[str, float]]:
    narrative = NARRATIVES.get(candidate.ticker, {})
    access = 24.0
    price = _price_score(candidate.price_usd)
    market_cap = _market_cap_score(candidate.market_cap_usd)
    liquidity = _liquidity_score(candidate.volume_usd)
    momentum = _momentum_score(candidate.price_change_24h_pct, candidate.price_change_7d_pct, candidate.price_change_30d_pct)
    story = float(narrative.get("score", 7))
    portfolio = _portfolio_score(candidate.ticker, holdings)
    penalty = 0.0
    if candidate.price_change_24h_pct > 35:
        penalty += 8
    if candidate.market_cap_usd > 10_000_000_000:
        penalty += 10
    score = max(0.0, min(100.0, access + price + market_cap + liquidity + momentum + story + portfolio - penalty))
    return score, {
        "acesso": access,
        "preco": price,
        "assimetriaMarketCap": market_cap,
        "liquidez": liquidity,
        "momento": momentum,
        "narrativa": story,
        "carteiraAtual": portfolio,
        "penalidade": penalty,
    }


def _price_score(price: float) -> float:
    if price <= 0.01:
        return 14
    if price <= 0.05:
        return 13
    if price <= 0.20:
        return 11
    if price <= 1:
        return 8
    if price <= 2:
        return 5
    return 0


def _market_cap_score(market_cap: float) -> float:
    if market_cap <= 0:
        return 8
    if 50_000_000 <= market_cap <= 700_000_000:
        return 18
    if 700_000_000 < market_cap <= 2_000_000_000:
        return 14
    if 10_000_000 <= market_cap < 50_000_000:
        return 10
    if 2_000_000_000 < market_cap <= 8_000_000_000:
        return 7
    return 3


def _liquidity_score(volume: float) -> float:
    if volume >= 25_000_000:
        return 13
    if volume >= 5_000_000:
        return 11
    if volume >= 1_000_000:
        return 8
    if volume >= 250_000:
        return 4
    return 0


def _momentum_score(change_24h: float, change_7d: float, change_30d: float) -> float:
    score = 6.0
    if -25 <= change_30d <= 40:
        score += 4
    if -15 <= change_7d <= 25:
        score += 3
    if change_24h < -12:
        score -= 2
    if change_24h > 25 or change_7d > 60:
        score -= 4
    return max(0, min(13, score))


def _portfolio_score(symbol: str, holdings: dict[str, dict]) -> float:
    holding = holdings.get(symbol)
    if not holding:
        return 0
    value = _float(holding.get("currentValue"))
    return_pct = _float(holding.get("returnPct"))
    score = 2.0
    if value < 100:
        score += 2
    if return_pct < -10:
        score += 2
    return min(score, 6)


def _selection_reason(candidate: MarketCandidate, holding: dict | None) -> str:
    narrative = NARRATIVES.get(candidate.ticker, {})
    base = narrative.get("thesis") or "assimetria em altcoin liquida listada na Binance."
    if holding:
        return f"Reforcar tese existente: {base} A posicao ja esta na carteira, entao o motor compara oportunidade externa com exposicao atual."
    return f"Nova oportunidade de estudo: {base} Passou nos filtros de acesso, preco, liquidez e assimetria."


def _candidate_from_research(report: dict | None, fallback: dict) -> dict:
    if not report:
        return fallback
    merged = dict(fallback)
    tokenomics = report.get("tokenomics") or {}
    market = report.get("market") or {}
    merged["ticker"] = report.get("ticker") or merged.get("ticker")
    merged["name"] = report.get("name") or merged.get("name")
    merged["alphaScore"] = report.get("researchScore", merged.get("alphaScore", 0))
    merged["decisionType"] = report.get("decisionType") or merged.get("decisionType")
    merged["selectionReason"] = report.get("finalVerdict") or merged.get("selectionReason")
    merged["researchReport"] = report
    merged["priceUsd"] = tokenomics.get("priceUsd", merged.get("priceUsd", 0))
    merged["marketCapUsd"] = tokenomics.get("marketCapUsd", merged.get("marketCapUsd", 0))
    merged["volumeUsd"] = tokenomics.get("volumeUsd", merged.get("volumeUsd", 0))
    merged["priceChange24hPct"] = market.get("priceChange24hPct", merged.get("priceChange24hPct", 0))
    merged["priceChange7dPct"] = market.get("priceChange7dPct", merged.get("priceChange7dPct", 0))
    merged["priceChange30dPct"] = market.get("priceChange30dPct", merged.get("priceChange30dPct", 0))
    merged["binancePairs"] = market.get("binancePairs") or merged.get("binancePairs", [])
    merged["source"] = market.get("source") or merged.get("source")
    return merged


def _build_payload(
    selected: dict,
    ranking: list[dict],
    holdings: dict[str, dict],
    current_date: date,
    *,
    live: bool,
    research: dict | None = None,
) -> dict:
    themes = NARRATIVES.get(selected["ticker"], {}).get("themes", [])
    decision_label = "Reforcar tese existente" if selected["decisionType"] == "reforcar_tese_existente" else "Nova oportunidade do mes"
    report = selected.get("researchReport") or {}
    research_reports = (research or {}).get("reports") or []
    return {
        "ticker": selected["ticker"],
        "name": selected["name"],
        "title": "Cripto do mes",
        "category": "Oportunidade assimetrica Binance",
        "riskLevel": "extremo",
        "reviewFrequency": "Mensal",
        "reviewMonth": current_date.strftime("%Y-%m"),
        "selectionScore": selected["alphaScore"],
        "researchScore": report.get("researchScore", selected["alphaScore"]),
        "selectionStatus": "selecionada_por_research_engine",
        "decisionType": selected["decisionType"],
        "decisionLabel": decision_label,
        "conviction": report.get("conviction"),
        "researchStatus": report.get("researchStatus"),
        "source": "Screener Alpha Crypto mensal + Crypto Research Engine com Binance, CoinMarketCap e CoinGecko quando disponiveis.",
        "dataMode": "live" if live else "fallback",
        "allocationGuardrail": "Exposicao especulativa pequena, fora do nucleo patrimonial e da reserva. Tese pode falhar totalmente.",
        "exchangeAccess": f"Disponivel na Binance Spot via {', '.join(selected['binancePairs'])}. Compra em BRL pode exigir conversao para USDT.",
        "binancePairs": selected["binancePairs"],
        "priceUsd": selected["priceUsd"],
        "marketCapUsd": selected["marketCapUsd"],
        "volumeUsd": selected["volumeUsd"],
        "priceChange24hPct": selected["priceChange24hPct"],
        "priceChange7dPct": selected["priceChange7dPct"],
        "priceChange30dPct": selected["priceChange30dPct"],
        "unitPriceRange": _unit_price_label(selected["priceUsd"]),
        "marketCapProfile": _market_cap_label(selected["marketCapUsd"]),
        "thesis": (
            f"{selected['ticker']} foi escolhida pelo ranking mensal de assimetria. "
            f"A leitura central e: {selected['selectionReason']} "
            "O objetivo e buscar uma candidata com potencial de alavancar a parcela especulativa, sem promessa de resultado."
        ),
        "whySelected": [
            f"{decision_label}: {selected['selectionReason']}",
            f"Research Score: {report.get('researchScore', selected['alphaScore'])}/100.",
            f"Conviccao: {report.get('conviction', 'em validacao')}.",
            f"Temas observados: {', '.join(themes) if themes else 'assimetria, liquidez e acesso Binance'}.",
            "Passou no filtro operacional: compra simples em exchange grande antes de qualquer tese de valorizacao.",
        ],
        "watchpoints": [
            "Checar se o movimento recente nao foi pump curto antes de aportar.",
            "Comparar market cap e supply antes de imaginar multiplicacoes extremas.",
            "Acompanhar perda de volume, retirada de pares, falhas de roadmap, hacks, unlocks e risco regulatorio.",
            "Se a moeda ja estiver na carteira, reforco so faz sentido se a tese continuar viva e a exposicao ainda for pequena.",
        ],
        "monthlyScanCriteria": [
            "Varredura externa primeiro: Binance USDT Spot, volume, preco, market cap e narrativa.",
            "CoinMarketCap e CoinGecko enriquecem preco, market cap, volume e variacao de 7/30 dias quando disponiveis.",
            "O ranking procura assimetria: preco baixo, market cap com espaco, liquidez real e narrativa forte.",
            "Depois do ranking externo, o Crypto Research Engine valida tokenomics, catalisadores, red flags e cenarios.",
            "A candidata pode repetir em meses diferentes, mas precisa continuar vencendo o ranking mensal.",
        ],
        "realityCheck": [
            "O sistema busca oportunidade, nao certeza. Nenhuma cripto e tratada como garantia de ficar milionario.",
            "Preco unitario baixo nao significa ativo barato; supply, market cap e volume mandam mais.",
            "Cripto do mes e exposicao de risco extremo, separada da carteira principal de dividendos.",
            "Se a melhor oportunidade do ranking for uma moeda que voce ja tem, o sistema pode classificar como reforco de tese existente.",
        ],
        "ranking": ranking,
        "research": research or {},
        "researchReport": report,
        "researchRanking": research_reports,
        "portfolioCryptoTickers": sorted(holdings.keys()),
        "previousCandidate": {
            "ticker": "PEPETO",
            "status": "substituida_por_acesso",
            "reason": "Falhou no criterio operacional: compra complexa, sem disponibilidade direta na Binance no momento do estudo.",
        },
    }


def _fallback_candidate(holdings: dict[str, dict]) -> dict:
    candidate = dict(FALLBACK_CANDIDATE)
    holding = holdings.get(candidate["ticker"])
    candidate["decisionType"] = "reforcar_tese_existente" if holding else "nova_oportunidade"
    candidate["alreadyInPortfolio"] = bool(holding)
    candidate["currentPortfolioValue"] = round(_float((holding or {}).get("currentValue")), 2)
    candidate["portfolioReturnPct"] = round(_float((holding or {}).get("returnPct")), 2)
    candidate["scoreBreakdown"] = {"fallback": 78.0}
    return candidate


def _current_crypto_context(db: Session | None, user_id: str | None) -> dict[str, dict]:
    if db is None or not user_id:
        return {}
    try:
        positions = get_positions(db, user_id)
    except Exception:
        return {}
    return {
        position["ticker"].upper(): position
        for position in positions
        if str(position.get("class") or "").lower() in {"cripto", "crypto"}
    }


def _load_cache(db: Session, user_id: str, key: str) -> dict | None:
    preference = (
        db.execute(select(UserPreference).where(UserPreference.user_id == user_id, UserPreference.key == key))
        .scalars()
        .first()
    )
    if not preference or not preference.value_json:
        return None
    try:
        return json.loads(preference.value_json)
    except Exception:
        return None


def _save_cache(db: Session, user_id: str, key: str, payload: dict) -> None:
    preference = (
        db.execute(select(UserPreference).where(UserPreference.user_id == user_id, UserPreference.key == key))
        .scalars()
        .first()
    )
    if preference is None:
        preference = UserPreference(user_id=user_id, key=key)
        db.add(preference)
    preference.value_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    preference.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()


def _is_candidate_symbol(symbol: str) -> bool:
    if not symbol or symbol in STABLE_OR_NON_SPECULATIVE:
        return False
    if any(symbol.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
        return False
    return True


def _unit_price_label(price: float) -> str:
    if price <= 0:
        return "preco indisponivel"
    if price < 0.01:
        return "abaixo de 1 centavo de dolar"
    if price < 0.10:
        return "centavos de dolar"
    if price < 1:
        return "abaixo de 1 dolar"
    return "baixo valor relativo"


def _market_cap_label(market_cap: float) -> str:
    if market_cap <= 0:
        return "market cap indisponivel"
    if market_cap < 100_000_000:
        return "micro/small cap especulativa"
    if market_cap < 1_000_000_000:
        return "small/mid cap especulativa"
    if market_cap < 5_000_000_000:
        return "mid cap com menor assimetria"
    return "large cap, menor perfil moonshot"


def _first_number(*values) -> float:
    for value in values:
        number = _float(value)
        if number != 0:
            return number
    return 0.0


def _float(value) -> float:
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0.0
    except Exception:
        return 0.0
