from __future__ import annotations

from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Asset, MarketSnapshot
from app.services.data_lineage import record_data_evidence
from app.services.market_data.v2.engine import MarketDataEngine
from app.services.market_data.v2.contracts import DATA_TYPE_FUNDAMENTALS, MarketDataRequest, MarketDataUnavailable, NormalizedMarketData
from app.services.portfolio import get_positions


SNAPSHOT_FIELD_MAP = {
    "price": "price",
    "dividend_yield": "dividend_yield",
    "payout": "payout",
    "revenue_growth": "revenue_growth",
    "profit_growth": "profit_growth",
    "net_margin": "net_margin",
    "roe": "roe",
    "roic": "roic",
    "debt_to_ebitda": "debt_to_ebitda",
    "pe_ratio": "pe_ratio",
    "pvp": "pvp",
}

FIELD_PROVIDER_PRIORITY = {
    "price": ["brapi", "dados_mercado", "fmp", "twelvedata", "fundamentus"],
    "dividend_yield": ["dados_mercado", "fmp", "fundamentus", "brapi", "twelvedata"],
    "payout": ["dados_mercado", "fmp", "fundamentus", "brapi", "twelvedata"],
    "revenue_growth": ["dados_mercado", "fmp", "twelvedata", "fundamentus", "brapi"],
    "profit_growth": ["dados_mercado", "fmp", "twelvedata", "fundamentus", "brapi"],
    "net_margin": ["dados_mercado", "fmp", "fundamentus", "twelvedata", "brapi"],
    "roe": ["dados_mercado", "fmp", "fundamentus", "twelvedata", "brapi"],
    "roic": ["dados_mercado", "fmp", "fundamentus", "twelvedata", "brapi"],
    "debt_to_ebitda": ["dados_mercado", "fmp", "fundamentus", "twelvedata", "brapi"],
    "pe_ratio": ["brapi", "dados_mercado", "fmp", "fundamentus", "twelvedata"],
    "pvp": ["dados_mercado", "fmp", "fundamentus", "twelvedata", "brapi"],
}


def _decimal(value: float | int | str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _percent(value: float | int | str | None) -> Decimal | None:
    decimal = _decimal(value)
    if decimal is None:
        return None
    if Decimal("-1") < decimal < Decimal("1"):
        return decimal * Decimal("100")
    return decimal


def _set_if_present(snapshot: MarketSnapshot, field: str, value: Decimal | None) -> bool:
    if value is None:
        return False
    setattr(snapshot, field, value)
    return True


def sync_asset_market_data(db: Session, asset: Asset, timeout: float = 6.0) -> bool:
    settings = get_settings()
    request = MarketDataRequest(
        symbol=asset.ticker,
        asset_id=asset.id,
        provider_symbol=asset.provider_symbol or asset.ticker,
        market=asset.market or "B3",
        asset_class=asset.asset_class,
        currency=asset.currency or "BRL",
    )
    engine = MarketDataEngine(db=db)

    try:
        records = engine.collect(DATA_TYPE_FUNDAMENTALS, request, include_mock=False)
    except MarketDataUnavailable:
        records = []

    if not records and settings.market_data_provider.lower() == "mock":
        try:
            records = [engine.fetch(DATA_TYPE_FUNDAMENTALS, request)]
        except MarketDataUnavailable:
            records = []
    if not records:
        return False

    data = _merge_fundamental_records(records)
    provider = str((data.get("sources") or ["market_data_engine"])[0])
    snapshot = asset.snapshot
    if snapshot is None:
        snapshot = MarketSnapshot(asset_id=asset.id, price=asset.last_price or 0)
        db.add(snapshot)
        db.flush()

    changed = False
    price = _decimal(data.get("price"))
    if price is not None and price > 0:
        asset.last_price = price
        snapshot.price = price
        changed = True

    currency = _first_currency(records) or data.get("currency")
    if currency:
        asset.currency = currency

    for payload_field, snapshot_field in SNAPSHOT_FIELD_MAP.items():
        if payload_field == "price":
            continue
        normalizer = _percent if payload_field in {"dividend_yield", "payout", "revenue_growth", "profit_growth", "net_margin", "roe", "roic"} else _decimal
        changed = _set_if_present(snapshot, snapshot_field, normalizer(data.get(payload_field))) or changed
    _record_market_evidence(db, asset, data, provider)
    return changed


def _record_market_evidence(db: Session, asset: Asset, data: dict, provider: str) -> None:
    sources = data.get("sources") or []
    source_type = "fallback" if provider in {"mock", "fallback"} else "provider"
    for field in SNAPSHOT_FIELD_MAP:
        value = data.get(field)
        if value in (None, "", 0, 0.0):
            continue
        record_data_evidence(
            db,
            domain="market_data",
            field_name=field,
            asset_id=asset.id,
            value_numeric=value if field != "currency" else None,
            currency=asset.currency or "",
            provider=provider,
            source_type=source_type,
            source_ref=f"asset:{asset.ticker}",
            confidence=82 if source_type == "provider" else 45,
            quality_score=82 if source_type == "provider" else 45,
            status="ok" if source_type == "provider" else "fallback",
            metadata={"ticker": asset.ticker, "sources": sources},
        )


def _merge_fundamental_records(records: list[NormalizedMarketData]) -> dict:
    merged: dict[str, float | str] = {"sources": [record.provider for record in records]}
    for field in SNAPSHOT_FIELD_MAP:
        value = _best_field_value(field, records)
        if value not in (None, "", 0, 0.0):
            merged[field] = value
    return merged


def _best_field_value(field: str, records: list[NormalizedMarketData]):
    priority = FIELD_PROVIDER_PRIORITY.get(field, [])
    candidates = []
    for record in records:
        value = record.payload.get(field)
        if value in (None, "", 0, 0.0):
            continue
        try:
            numeric = float(value)
        except Exception:
            numeric = 0
        if numeric == 0:
            continue
        provider_rank = priority.index(record.provider) if record.provider in priority else len(priority) + 5
        candidates.append((provider_rank, -float(record.quality_score or 0), value))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def _first_currency(records: list[NormalizedMarketData]) -> str:
    for record in records:
        if record.currency:
            return record.currency
    return ""


def sync_user_assets(db: Session, user_id: str) -> dict:
    positions = get_positions(db, user_id)
    updated: list[str] = []
    skipped: list[str] = []
    for position in positions:
        asset = db.get(Asset, position["assetId"])
        if asset is None:
            continue
        if sync_asset_market_data(db, asset, timeout=15.0):
            updated.append(asset.ticker)
        else:
            skipped.append(asset.ticker)
    db.commit()
    return {"updated": updated, "skipped": skipped}
