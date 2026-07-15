from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from math import isfinite
from statistics import mean
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Asset, AssetFact, AssetMetricDivergence, Dividend, MarketDataCacheEntry, Transaction
from app.services.asset_taxonomy import classify_position
from app.services.portfolio import get_positions


PRIMARY_PRICE_PROVIDERS = {"brapi", "yahoo_finance", "fmp", "twelvedata", "coingecko", "coinmarketcap"}
FALLBACK_MARKERS = {"fallback", "mock", "foundation", "manual_only", "not_applicable", "fallback_current_price"}


def build_data_confidence_audit(
    db: Session,
    user_id: str,
    *,
    backtest_sources: dict[str, str] | None = None,
    backtest_warnings: list[str] | None = None,
) -> dict:
    """Create an auditable data-confidence layer for the user's portfolio.

    This engine does not judge whether an asset is good. It judges whether the
    system knows where each relevant number came from and how reliable that
    number is for analysis, backtest and recommendation governance.
    """

    positions = get_positions(db, user_id)
    transaction_counts = _transaction_counts(db, user_id)
    dividend_rows = _dividends_by_asset(db, user_id)
    facts_by_asset = _facts_by_asset(db)
    divergences_by_asset = _divergences_by_asset(db)
    cache_by_symbol = _cache_by_symbol(db)
    source_map = backtest_sources or {}

    rows = []
    for position in positions:
        asset = db.get(Asset, position.get("assetId")) if position.get("assetId") else None
        if asset is None:
            continue
        taxonomy = classify_position(position, asset)
        ticker = asset.ticker
        fields = [
            _field_price(asset, position, cache_by_symbol, source_map.get(ticker)),
            _field_history(ticker, source_map.get(ticker), backtest_warnings or []),
            _field_fundamentals(facts_by_asset.get(asset.id, []), asset.snapshot),
            _field_income(dividend_rows.get(asset.id, []), taxonomy),
            _field_transactions(transaction_counts.get(asset.id, 0)),
            _field_divergence(divergences_by_asset.get(asset.id, [])),
        ]
        score = _weighted_score(fields)
        rows.append(
            {
                "assetId": asset.id,
                "ticker": ticker,
                "name": asset.name,
                "assetClass": asset.asset_class,
                "score": score,
                "classification": _classification(score),
                "status": _status(score),
                "hasFallback": any(_is_fallback(field.get("source")) or field.get("status") == "fallback" for field in fields),
                "fieldAudits": fields,
                "mainLimitation": _main_limitation(fields),
                "lastCheckedAt": datetime.now(UTC).isoformat(),
            }
        )

    scores = [row["score"] for row in rows]
    fallback_assets = [row for row in rows if row["hasFallback"]]
    overall = round(mean(scores), 2) if scores else 0.0
    source_counts = defaultdict(int)
    for row in rows:
        for field in row["fieldAudits"]:
            source_counts[str(field.get("source") or "unknown")] += 1

    return {
        "status": "operational",
        "title": "Data Confidence Engine",
        "updatedAt": datetime.now(UTC).isoformat(),
        "overallScore": overall,
        "classification": _classification(overall),
        "assetCount": len(rows),
        "fallbackAssetCount": len(fallback_assets),
        "sourceCounts": dict(sorted(source_counts.items())),
        "assetRows": sorted(rows, key=lambda item: item["score"]),
        "plainLanguage": _plain_language(overall, len(fallback_assets), len(rows)),
        "nonNegotiables": [
            "Todo numero relevante precisa ter fonte.",
            "Fallback nao e erro, mas reduz confianca e precisa aparecer na tela.",
            "Divergencia entre fontes nunca deve ser escondida.",
            "Recomendacao institucional so pode usar dado com rastreabilidade minima.",
        ],
    }


def _field_price(asset: Asset, position: dict, cache_by_symbol: dict[str, list[MarketDataCacheEntry]], source_from_backtest: str | None) -> dict:
    cache_rows = cache_by_symbol.get(asset.ticker.upper()) or []
    quote_cache = next((row for row in cache_rows if row.data_type == "quote"), None)
    source = source_from_backtest or (quote_cache.provider if quote_cache else "manual_snapshot")
    quality = _float(quote_cache.quality_score if quote_cache else 62)
    if _is_fallback(source):
        quality = min(quality, 45)
    if _float(position.get("currentPrice")) <= 0:
        quality = 15
    return _field(
        "price",
        "Preco atual",
        source,
        quality,
        "ok" if quality >= 65 else "fallback",
        f"Preco atual usado: R$ {_float(position.get('currentPrice')):,.2f}.",
    )


def _field_history(ticker: str, source: str | None, warnings: list[str]) -> dict:
    warning_hit = any(ticker in str(item) for item in warnings)
    provider = source or "history_not_requested"
    if warning_hit or _is_fallback(provider):
        return _field("history", "Historico de precos", provider, 42, "fallback", "Historico incompleto ou usando preco atual como fallback.")
    return _field("history", "Historico de precos", provider, 82 if provider in PRIMARY_PRICE_PROVIDERS else 68, "ok", "Historico usado no backtest com provider identificado.")


def _field_fundamentals(facts: list[AssetFact], snapshot: Any) -> dict:
    fact_score = _average([_float(fact.confidence) for fact in facts])
    snapshot_fields = 0
    if snapshot is not None:
        snapshot_fields = sum(
            1
            for value in [
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
            ]
            if abs(_float(value)) > 0
        )
    source = ",".join(sorted({fact.source for fact in facts})) if facts else ("market_snapshot" if snapshot_fields else "manual_only")
    quality = max(fact_score, min(86, 42 + snapshot_fields * 5))
    status = "ok" if quality >= 70 else "partial" if quality >= 45 else "fallback"
    return _field("fundamentals", "Fundamentos", source, quality, status, f"{len(facts)} fatos tratados e {snapshot_fields} campos de snapshot preenchidos.")


def _field_income(dividends: list[Dividend], taxonomy: Any) -> dict:
    if taxonomy.is_crypto:
        return _field("income", "Proventos", "not_applicable", 100, "ok", "Cripto nao possui proventos tradicionais no motor atual.")
    if not dividends:
        return _field("income", "Proventos/JCP", "manual_missing", 36, "fallback", "Nenhum provento interno registrado para este ativo.")
    sources = ",".join(sorted({dividend.source for dividend in dividends}))
    quality = min(92, 52 + len(dividends) * 7)
    return _field("income", "Proventos/JCP", sources, quality, "ok" if quality >= 70 else "partial", f"{len(dividends)} provento(s) registrado(s) internamente.")


def _field_transactions(count: int) -> dict:
    if count <= 0:
        return _field("transactions", "Movimentacoes", "manual_missing", 20, "fallback", "Sem compra/venda registrada para calcular preco medio.")
    return _field("transactions", "Movimentacoes", "user_ledger", min(96, 72 + count * 4), "ok", f"{count} movimentacao(oes) registrada(s) pelo usuario.")


def _field_divergence(divergences: list[AssetMetricDivergence]) -> dict:
    open_items = [item for item in divergences if item.status == "open"]
    if not open_items:
        return _field("divergence", "Divergencia entre fontes", "knowledge_engine", 88, "ok", "Nenhuma divergencia aberta relevante.")
    worst = max(_float(item.divergence_pct) for item in open_items)
    quality = max(25, 80 - len(open_items) * 10 - min(30, worst))
    return _field("divergence", "Divergencia entre fontes", "knowledge_engine", quality, "attention", f"{len(open_items)} divergencia(s) aberta(s); maior diferenca {worst:.2f}%.")


def _field(field_id: str, label: str, source: str, score: float, status: str, reading: str) -> dict:
    return {
        "id": field_id,
        "label": label,
        "source": source,
        "score": round(_clamp(score), 2),
        "status": status,
        "reading": reading,
    }


def _transaction_counts(db: Session, user_id: str) -> dict[str, int]:
    rows = db.execute(select(Transaction).where(Transaction.user_id == user_id)).scalars().all()
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.asset_id] += 1
    return counts


def _dividends_by_asset(db: Session, user_id: str) -> dict[str, list[Dividend]]:
    rows = db.execute(select(Dividend).where(Dividend.user_id == user_id)).scalars().all()
    grouped: dict[str, list[Dividend]] = defaultdict(list)
    for row in rows:
        grouped[row.asset_id].append(row)
    return grouped


def _facts_by_asset(db: Session) -> dict[str, list[AssetFact]]:
    rows = db.execute(select(AssetFact).order_by(desc(AssetFact.as_of))).scalars().all()
    grouped: dict[str, list[AssetFact]] = defaultdict(list)
    for row in rows:
        grouped[row.asset_id].append(row)
    return grouped


def _divergences_by_asset(db: Session) -> dict[str, list[AssetMetricDivergence]]:
    rows = db.execute(select(AssetMetricDivergence).order_by(desc(AssetMetricDivergence.created_at))).scalars().all()
    grouped: dict[str, list[AssetMetricDivergence]] = defaultdict(list)
    for row in rows:
        grouped[row.asset_id].append(row)
    return grouped


def _cache_by_symbol(db: Session) -> dict[str, list[MarketDataCacheEntry]]:
    rows = db.execute(select(MarketDataCacheEntry).order_by(desc(MarketDataCacheEntry.updated_at))).scalars().all()
    grouped: dict[str, list[MarketDataCacheEntry]] = defaultdict(list)
    for row in rows:
        key = str(row.cache_key or "").upper()
        for part in key.replace(":", "|").split("|"):
            if part and len(part) <= 16:
                grouped[part].append(row)
    return grouped


def _weighted_score(fields: list[dict]) -> float:
    weights = {
        "price": 0.20,
        "history": 0.20,
        "fundamentals": 0.20,
        "income": 0.14,
        "transactions": 0.14,
        "divergence": 0.12,
    }
    total = sum(_float(field.get("score")) * weights.get(field.get("id"), 0.10) for field in fields)
    return round(_clamp(total), 2)


def _main_limitation(fields: list[dict]) -> str:
    weakest = min(fields, key=lambda item: _float(item.get("score")), default=None)
    if not weakest or _float(weakest.get("score")) >= 70:
        return "Dados principais rastreados em nivel saudavel."
    return f"{weakest['label']}: {weakest['reading']}"


def _plain_language(score: float, fallback_count: int, total_count: int) -> list[str]:
    return [
        f"A confianca de dados da carteira esta em {score:.0f}/100.",
        f"{fallback_count} de {total_count} ativos ainda possuem algum campo com fallback, fonte manual ou historico incompleto.",
        "Quando a confianca for baixa, o Alpha deve reduzir conviccao e mostrar a limitacao antes de qualquer tese.",
    ]


def _classification(score: float) -> str:
    if score >= 84:
        return "Auditavel forte"
    if score >= 72:
        return "Auditavel bom"
    if score >= 58:
        return "Parcialmente auditavel"
    return "Confianca fraca"


def _status(score: float) -> str:
    if score >= 72:
        return "ok"
    if score >= 58:
        return "attention"
    return "blocker"


def _is_fallback(source: str | None) -> bool:
    raw = str(source or "").lower()
    return any(marker in raw for marker in FALLBACK_MARKERS)


def _average(values: list[float]) -> float:
    clean = [_float(value) for value in values if _float(value) > 0]
    return round(mean(clean), 2) if clean else 0.0


def _float(value: Any) -> float:
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0.0
    except Exception:
        return 0.0


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))
