from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models import Asset, AssetFact, MarketDataCacheEntry
from app.services.alpha_b3_screener import OFFICIAL_TARGET_WEIGHTS
from app.services.portfolio import get_positions
from app.wealth_os.contracts import (
    AssetResearchReport,
    DataConfidenceItem,
    ResearchCenterReport,
    ResearchEvidence,
    ResearchNewsItem,
)
from app.wealth_os.event_engine_v2 import build_event_stream_v2
from app.wealth_os.utils import as_float


RESEARCH_CACHE_PREFIX = "research-news-v1"
NEWS_TTL_SECONDS = 60 * 60 * 6
CORE_FACTS = {
    "price": "Preco atual",
    "dividend_yield": "Dividend yield",
    "payout": "Payout",
    "pe_ratio": "P/L",
    "pvp": "P/VP",
    "ev_ebitda": "EV/EBITDA",
    "revenue_growth": "Crescimento de receita",
    "profit_growth": "Crescimento de lucro",
    "net_margin": "Margem liquida",
    "roe": "ROE",
    "roic": "ROIC",
    "debt_to_ebitda": "Divida liquida/EBITDA",
    "market_value": "Valor de mercado",
}


def build_research_center(db: Session, user_id: str, *, limit: int = 12, refresh_news: bool = False) -> ResearchCenterReport:
    assets = _research_universe(db, user_id, limit=limit)
    reports = [build_asset_research_report(db, user_id, asset.ticker, refresh_news=refresh_news) for asset in assets]
    news_feed = sorted(
        [item for report in reports for item in report.news],
        key=lambda item: item.publishedAt,
        reverse=True,
    )[:20]
    coverage = {
        "assets": len(reports),
        "withEvidence": sum(1 for report in reports if report.evidence),
        "withNews": sum(1 for report in reports if report.news),
        "newsItems": len(news_feed),
    }
    source_health = _source_health(reports)
    status = "operacional" if reports else "sem_ativos"
    headline = (
        "Research & News Engine consolidou evidencias internas, fundamentos e noticias disponiveis."
        if reports
        else "Research & News Engine aguardando ativos para montar o centro de evidencias."
    )
    return ResearchCenterReport(
        status=status,
        headline=headline,
        coverage=coverage,
        sourceHealth=source_health,
        reports=reports,
        newsFeed=news_feed,
    )


def build_asset_research_report(db: Session, user_id: str, ticker: str, *, refresh_news: bool = False) -> AssetResearchReport:
    asset = _find_asset(db, ticker)
    if asset is None:
        return _missing_asset_report(ticker)

    facts = _latest_facts(db, asset.id)
    evidence = _evidence_from_asset(asset, facts)
    evidence.extend(_event_evidence(db, user_id, asset.ticker))
    news = _fetch_news(db, asset, refresh=refresh_news)
    data_gaps = _data_gaps(asset, facts, news)
    risks = _risk_readings(asset, facts, news)
    opportunities = _opportunity_readings(asset, facts, news)
    score = _research_score(asset, facts, evidence, news, data_gaps)
    status = _status(score, data_gaps)
    headline = _headline(asset, score, news, data_gaps)

    return AssetResearchReport(
        ticker=asset.ticker,
        name=asset.name,
        assetClass=asset.asset_class,
        sector=asset.sector,
        researchScore=score,
        status=status,
        headline=headline,
        thesis=_thesis(asset, facts, news),
        evidence=evidence[:12],
        news=news[:8],
        risks=risks,
        opportunities=opportunities,
        dataGaps=data_gaps,
        confidence=_confidence(score),
        updatedAt=datetime.now(UTC).isoformat(),
    )


def _research_universe(db: Session, user_id: str, *, limit: int) -> list[Asset]:
    positions = get_positions(db, user_id)
    tickers = [item["ticker"] for item in positions]
    tickers.extend(OFFICIAL_TARGET_WEIGHTS.keys())
    unique = list(dict.fromkeys(tickers))[: max(1, limit)]
    if not unique:
        return []
    return (
        db.execute(select(Asset).options(joinedload(Asset.snapshot)).where(Asset.ticker.in_(unique)))
        .scalars()
        .all()
    )


def _find_asset(db: Session, ticker: str) -> Asset | None:
    normalized = ticker.upper().strip()
    return (
        db.execute(select(Asset).options(joinedload(Asset.snapshot)).where(Asset.ticker == normalized))
        .scalars()
        .first()
    )


def _latest_facts(db: Session, asset_id: str) -> dict[str, AssetFact]:
    rows = (
        db.execute(
            select(AssetFact)
            .where(AssetFact.asset_id == asset_id, AssetFact.period == "latest")
            .order_by(AssetFact.updated_at.desc())
        )
        .scalars()
        .all()
    )
    facts: dict[str, AssetFact] = {}
    for row in rows:
        facts.setdefault(row.metric_key, row)
    return facts


def _evidence_from_asset(asset: Asset, facts: dict[str, AssetFact]) -> list[ResearchEvidence]:
    evidence: list[ResearchEvidence] = []
    snapshot = asset.snapshot
    snapshot_values = {
        "price": snapshot.price if snapshot else asset.last_price,
        "dividend_yield": snapshot.dividend_yield if snapshot else None,
        "payout": snapshot.payout if snapshot else None,
        "pe_ratio": snapshot.pe_ratio if snapshot else None,
        "pvp": snapshot.pvp if snapshot else None,
        "revenue_growth": snapshot.revenue_growth if snapshot else None,
        "profit_growth": snapshot.profit_growth if snapshot else None,
        "net_margin": snapshot.net_margin if snapshot else None,
        "roe": snapshot.roe if snapshot else None,
        "roic": snapshot.roic if snapshot else None,
        "debt_to_ebitda": snapshot.debt_to_ebitda if snapshot else None,
    }
    for key, label in CORE_FACTS.items():
        fact = facts.get(key)
        value = fact.value_numeric if fact and fact.value_numeric is not None else snapshot_values.get(key)
        if value in (None, "", 0, Decimal("0")):
            continue
        source = fact.source if fact else "market_snapshot"
        confidence = as_float(fact.confidence if fact else 62)
        as_of = fact.as_of.isoformat() if fact else (snapshot.updated_at.isoformat() if snapshot else datetime.now(UTC).isoformat())
        evidence.append(
            ResearchEvidence(
                id=f"{asset.ticker}-{key}-{source}",
                type="fundamental",
                source=source,
                title=label,
                reading=f"{label}: {_format_value(key, value)}.",
                confidenceScore=confidence,
                asOf=as_of,
            )
        )
    return evidence


def _event_evidence(db: Session, user_id: str, ticker: str) -> list[ResearchEvidence]:
    events = [event for event in build_event_stream_v2(db, user_id) if event.asset == ticker]
    evidence: list[ResearchEvidence] = []
    for event in events[:4]:
        evidence.append(
            ResearchEvidence(
                id=f"event-{event.id}",
                type="event",
                source=event.source,
                title=event.title,
                reading=f"{event.message} Impacto: {event.impact}",
                confidenceScore=70 if event.confidence == "media" else 85 if event.confidence == "alta" else 45,
                asOf=event.triggeredAt,
            )
        )
    return evidence


def _fetch_news(db: Session, asset: Asset, *, refresh: bool) -> list[ResearchNewsItem]:
    settings = get_settings()
    if not settings.fmp_api_key or asset.asset_class.lower() in {"cripto", "crypto"}:
        return []
    cache_key = f"{RESEARCH_CACHE_PREFIX}:fmp:{asset.ticker}"
    if not refresh:
        cached = _get_cached_news(db, cache_key)
        if cached is not None:
            return [_news_from_dict(item) for item in cached]
    rows = _fetch_fmp_stock_news(asset)
    payload = [_news_to_dict(item) for item in rows]
    try:
        _set_cached_news(db, cache_key, payload)
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    return rows


def _fetch_fmp_stock_news(asset: Asset) -> list[ResearchNewsItem]:
    settings = get_settings()
    symbol = _provider_symbol(asset)
    params = {"symbols": symbol, "limit": 8, "apikey": settings.fmp_api_key}
    url = f"{settings.fmp_base_url.rstrip('/')}/news/stock"
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        _record_news_failure(asset.ticker, exc)
        return []
    rows = data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    news: list[ResearchNewsItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or row.get("headline") or "").strip()
        if not title:
            continue
        published = str(row.get("publishedDate") or row.get("date") or row.get("publishedAt") or "")
        summary = str(row.get("text") or row.get("summary") or row.get("site") or "")[:420]
        source = str(row.get("site") or row.get("publisher") or "FMP")
        url_value = str(row.get("url") or "")
        news.append(
            ResearchNewsItem(
                id=_stable_id(asset.ticker, title, published),
                ticker=asset.ticker,
                title=title,
                summary=summary,
                source=source,
                publishedAt=published or datetime.now(UTC).isoformat(),
                url=url_value,
                sentiment=_sentiment(title, summary),
                relevanceScore=_relevance(title, summary),
            )
        )
    return news


def _record_news_failure(ticker: str, exc: Exception) -> None:
    # Failures are intentionally non-blocking. Provider telemetry is persisted
    # only when the engine has a DB session through cache operations.
    _ = (ticker, exc)


def _get_cached_news(db: Session, cache_key: str) -> list[dict] | None:
    row = db.execute(select(MarketDataCacheEntry).where(MarketDataCacheEntry.cache_key == cache_key)).scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at <= _utcnow_naive():
        return None
    try:
        payload = json.loads(row.payload_json)
    except ValueError:
        return None
    return payload if isinstance(payload, list) else None


def _set_cached_news(db: Session, cache_key: str, payload: list[dict]) -> None:
    expires_at = _utcnow_naive() + timedelta(seconds=NEWS_TTL_SECONDS)
    row = db.execute(select(MarketDataCacheEntry).where(MarketDataCacheEntry.cache_key == cache_key)).scalar_one_or_none()
    if row is None:
        row = MarketDataCacheEntry(cache_key=cache_key)
        db.add(row)
    row.provider = "fmp"
    row.data_type = "news"
    row.payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    row.quality_score = Decimal("70") if payload else Decimal("35")
    row.expires_at = expires_at
    row.updated_at = _utcnow_naive()
    db.flush()


def _data_gaps(asset: Asset, facts: dict[str, AssetFact], news: list[ResearchNewsItem]) -> list[str]:
    gaps = []
    if not asset.snapshot and not facts:
        gaps.append("Sem snapshot de mercado ou fatos tratados no Knowledge Engine.")
    missing = [label for key, label in CORE_FACTS.items() if key not in facts][:4]
    if missing:
        gaps.append("Faltam fatos tratados: " + ", ".join(missing) + ".")
    if not news and asset.asset_class.lower() not in {"cripto", "crypto"}:
        gaps.append("Sem noticias recentes no cache/FMP para este ativo.")
    if asset.sector in {"", "Nao classificado"}:
        gaps.append("Setor ainda nao classificado.")
    return gaps[:5]


def _risk_readings(asset: Asset, facts: dict[str, AssetFact], news: list[ResearchNewsItem]) -> list[str]:
    risks = []
    debt = _fact_value(facts, "debt_to_ebitda")
    payout = _fact_value(facts, "payout")
    pe = _fact_value(facts, "pe_ratio")
    if debt and debt >= 3:
        risks.append("Alavancagem acima do conforto inicial para renda passiva.")
    if payout and payout >= 90:
        risks.append("Payout elevado pode reduzir flexibilidade para reinvestimento e crescimento.")
    if pe and pe >= 25:
        risks.append("Multiplo P/L alto exige crescimento consistente para justificar valuation.")
    if any(item.sentiment == "negativo" for item in news[:5]):
        risks.append("Noticias recentes possuem tom negativo e exigem leitura manual.")
    if not risks:
        risks.append("Nenhum risco critico foi identificado com os dados disponiveis, mas a leitura depende da qualidade das fontes.")
    return risks[:4]


def _opportunity_readings(asset: Asset, facts: dict[str, AssetFact], news: list[ResearchNewsItem]) -> list[str]:
    opportunities = []
    dy = _fact_value(facts, "dividend_yield")
    roe = _fact_value(facts, "roe")
    growth = _fact_value(facts, "profit_growth")
    if dy and dy >= 6:
        opportunities.append("Yield de proventos acima do filtro inicial para renda passiva.")
    if roe and roe >= 15:
        opportunities.append("ROE indica boa rentabilidade sobre patrimonio com os dados atuais.")
    if growth and growth >= 8:
        opportunities.append("Crescimento de lucro aparece como fator positivo no recorte atual.")
    if any(item.sentiment == "positivo" for item in news[:5]):
        opportunities.append("Noticias recentes possuem tom positivo, mas precisam ser cruzadas com fundamentos.")
    if not opportunities:
        opportunities.append("O principal valor agora esta na continuidade do acompanhamento e melhoria de dados.")
    return opportunities[:4]


def _research_score(asset: Asset, facts: dict[str, AssetFact], evidence: list[ResearchEvidence], news: list[ResearchNewsItem], gaps: list[str]) -> float:
    fact_score = min(45, len([key for key in CORE_FACTS if key in facts]) * 4)
    snapshot_score = 18 if asset.snapshot else 0
    evidence_score = min(18, len(evidence) * 2)
    news_score = min(12, len(news) * 2)
    gap_penalty = min(25, len(gaps) * 5)
    return round(max(0, min(100, 25 + fact_score + snapshot_score + evidence_score + news_score - gap_penalty)), 2)


def _status(score: float, gaps: list[str]) -> str:
    if score >= 82 and len(gaps) <= 1:
        return "research_forte"
    if score >= 65:
        return "research_operacional"
    if score >= 45:
        return "research_parcial"
    return "dados_insuficientes"


def _confidence(score: float) -> str:
    if score >= 78:
        return "alta"
    if score >= 55:
        return "media"
    return "baixa"


def _headline(asset: Asset, score: float, news: list[ResearchNewsItem], gaps: list[str]) -> str:
    if score >= 78:
        return f"{asset.ticker} possui pesquisa estruturada com bom nivel de evidencias."
    if gaps:
        return f"{asset.ticker} ja tem leitura inicial, mas ainda faltam dados para research institucional completo."
    if news:
        return f"{asset.ticker} possui noticias recentes e evidencias internas para acompanhamento."
    return f"{asset.ticker} esta em acompanhamento pelo Research & News Engine."


def _thesis(asset: Asset, facts: dict[str, AssetFact], news: list[ResearchNewsItem]) -> str:
    dy = _fact_value(facts, "dividend_yield")
    roe = _fact_value(facts, "roe")
    parts = [f"{asset.ticker} atua em {asset.sector or 'setor ainda nao classificado'}."]
    if dy:
        parts.append(f"DY tratado em {dy:.2f}%.")
    if roe:
        parts.append(f"ROE tratado em {roe:.2f}%.")
    if news:
        parts.append(f"O motor encontrou {len(news)} noticia(s) recente(s) para cruzar com fundamentos.")
    else:
        parts.append("Sem noticia recente validada no cache, entao a tese depende mais dos dados internos e fundamentos.")
    return " ".join(parts)


def _source_health(reports: list[AssetResearchReport]) -> list[DataConfidenceItem]:
    total = len(reports)
    with_news = sum(1 for report in reports if report.news)
    with_evidence = sum(1 for report in reports if report.evidence)
    avg_score = round(sum(report.researchScore for report in reports) / total, 2) if total else 0
    return [
        DataConfidenceItem(
            area="Research interno",
            status="operacional" if with_evidence else "vazio",
            confidenceScore=round(with_evidence / total * 100, 2) if total else 0,
            source="Knowledge Engine + carteira + eventos",
            reading=f"{with_evidence}/{total} ativos possuem evidencias internas.",
            nextStep="Completar fundamentos e classificacoes para ampliar a cobertura.",
        ),
        DataConfidenceItem(
            area="Noticias",
            status="parcial" if with_news else "sem_feed_ativo",
            confidenceScore=round(with_news / total * 100, 2) if total else 0,
            source="FMP Stock News via backend/cache",
            reading=f"{with_news}/{total} ativos possuem noticias recentes no cache.",
            nextStep="Manter FMP_API_KEY configurada e usar refresh controlado quando necessario.",
        ),
        DataConfidenceItem(
            area="Score de research",
            status="operacional" if avg_score >= 50 else "em_construcao",
            confidenceScore=avg_score,
            source="Research & News Engine",
            reading=f"Score medio de research: {avg_score:.0f}/100.",
            nextStep="Aumentar fatos tratados, noticias e eventos oficiais por ativo.",
        ),
    ]


def _missing_asset_report(ticker: str) -> AssetResearchReport:
    return AssetResearchReport(
        ticker=ticker.upper().strip(),
        name=ticker.upper().strip(),
        assetClass="desconhecido",
        sector="Nao classificado",
        researchScore=0,
        status="ativo_nao_encontrado",
        headline="Ativo nao encontrado no Asset Engine.",
        thesis="Cadastre o ativo ou sincronize a base para iniciar o research.",
        evidence=[],
        news=[],
        risks=["Sem cadastro interno nao e possivel validar fundamentos, noticias ou eventos."],
        opportunities=[],
        dataGaps=["Ativo inexistente no banco local."],
        confidence="baixa",
        updatedAt=datetime.now(UTC).isoformat(),
    )


def _provider_symbol(asset: Asset) -> str:
    symbol = asset.provider_symbol or asset.ticker
    if asset.market.upper() in {"B3", "BR", "BRASIL"} and "." not in symbol and asset.asset_class.lower() not in {"cripto", "crypto"}:
        return f"{symbol}.SA"
    return symbol


def _fact_value(facts: dict[str, AssetFact], key: str) -> float:
    fact = facts.get(key)
    return as_float(fact.value_numeric if fact else 0)


def _format_value(key: str, value: Any) -> str:
    number = as_float(value)
    if key in {"dividend_yield", "payout", "revenue_growth", "profit_growth", "net_margin", "roe", "roic"}:
        return f"{number:.2f}%"
    if key in {"price", "revenue", "profit", "market_value"}:
        return f"R$ {number:,.2f}"
    return f"{number:.2f}"


def _sentiment(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    negative = ["queda", "loss", "cut", "corte", "lawsuit", "fraud", "downgrade", "debt", "prejuizo", "investigation"]
    positive = ["lucro", "profit", "upgrade", "record", "dividend", "dividendo", "growth", "alta", "beat", "expansion"]
    if any(term in text for term in negative):
        return "negativo"
    if any(term in text for term in positive):
        return "positivo"
    return "neutro"


def _relevance(title: str, summary: str) -> float:
    text = f"{title} {summary}".lower()
    score = 45
    for term in ["earnings", "resultado", "dividend", "dividendo", "guidance", "merger", "rating", "debt", "lucro"]:
        if term in text:
            score += 8
    return min(100, score)


def _stable_id(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _news_to_dict(item: ResearchNewsItem) -> dict:
    return {
        "id": item.id,
        "ticker": item.ticker,
        "title": item.title,
        "summary": item.summary,
        "source": item.source,
        "publishedAt": item.publishedAt,
        "url": item.url,
        "sentiment": item.sentiment,
        "relevanceScore": item.relevanceScore,
    }


def _news_from_dict(item: dict) -> ResearchNewsItem:
    return ResearchNewsItem(
        id=str(item.get("id") or ""),
        ticker=str(item.get("ticker") or ""),
        title=str(item.get("title") or ""),
        summary=str(item.get("summary") or ""),
        source=str(item.get("source") or ""),
        publishedAt=str(item.get("publishedAt") or ""),
        url=str(item.get("url") or ""),
        sentiment=str(item.get("sentiment") or "neutro"),
        relevanceScore=as_float(item.get("relevanceScore")),
    )


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
