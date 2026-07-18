from __future__ import annotations

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, MarketSnapshot, Transaction
from app.services.asset_taxonomy import classify_position
from app.services.data_lineage import record_data_evidence
from app.services.fixed_income import is_fixed_income_class
from app.services.market_data.v2.engine import MarketDataEngine
from app.services.market_data.v2.contracts import (
    DATA_TYPE_FUNDAMENTALS,
    DATA_TYPE_PRICE_HISTORY,
    DATA_TYPE_QUOTE,
    MarketDataRequest,
    MarketDataUnavailable,
    NormalizedMarketData,
)
from app.services.portfolio import get_positions


UNTRUSTED_SYNC_PROVIDERS = {"mock", "fallback"}
PRICE_HISTORY_PROVIDER_PRIORITY = ["yahoo_finance", "brapi", "fmp", "twelvedata", "dados_mercado"]

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
        quote_records = engine.collect(DATA_TYPE_QUOTE, request, include_mock=False)
    except MarketDataUnavailable:
        quote_records = []

    try:
        fundamental_records = engine.collect(DATA_TYPE_FUNDAMENTALS, request, include_mock=False)
    except MarketDataUnavailable:
        fundamental_records = []

    quote_records = _trusted_sync_records(quote_records)
    fundamental_records = _trusted_sync_records(fundamental_records)
    history_price_record = None
    if not quote_records:
        try:
            history_records = _trusted_sync_records(engine.collect(DATA_TYPE_PRICE_HISTORY, request, include_mock=False))
        except MarketDataUnavailable:
            history_records = []
        history_price_record = _latest_history_price_record(history_records)
    records = [*quote_records, *fundamental_records]
    if not records and history_price_record is None:
        return False

    data = _merge_fundamental_records(fundamental_records)
    quote_price = _best_field_value("price", quote_records)
    if quote_price not in (None, "", 0, 0.0):
        data["price"] = quote_price
        data["sources"] = [quote_records[0].provider, *data.get("sources", [])]
    elif history_price_record is not None:
        data["price"] = history_price_record["price"]
        data["sources"] = [history_price_record["provider"], *data.get("sources", [])]
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


def _trusted_sync_records(records: list[NormalizedMarketData]) -> list[NormalizedMarketData]:
    """Keep portfolio sync from persisting demo/fallback data as real prices."""

    trusted = []
    for record in records:
        provider = (record.provider or "").lower()
        if provider in UNTRUSTED_SYNC_PROVIDERS:
            continue
        trusted.append(record)
    return trusted


def _latest_history_price_record(records: list[NormalizedMarketData]) -> dict | None:
    candidates = []
    for record in records:
        prices = record.payload.get("prices") or []
        clean_prices = []
        for row in prices:
            if not isinstance(row, dict):
                continue
            value = row.get("close", row.get("price"))
            if value in (None, "", 0, 0.0):
                continue
            try:
                clean_prices.append({"date": str(row.get("date") or ""), "price": float(value)})
            except (TypeError, ValueError):
                continue
        if not clean_prices:
            continue
        clean_prices.sort(key=lambda item: item["date"])
        latest = clean_prices[-1]
        provider = (record.provider or "").lower()
        provider_rank = (
            PRICE_HISTORY_PROVIDER_PRIORITY.index(provider)
            if provider in PRICE_HISTORY_PROVIDER_PRIORITY
            else len(PRICE_HISTORY_PROVIDER_PRIORITY) + 5
        )
        candidates.append((provider_rank, -float(record.quality_score or 0), latest["date"], latest["price"], provider))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    _, _, latest_date, price, provider = candidates[0]
    return {"date": latest_date, "price": price, "provider": provider}


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
    repaired: list[str] = []
    for position in positions:
        asset = db.get(Asset, position["assetId"])
        if asset is None:
            continue
        taxonomy = classify_position(position, asset)
        if taxonomy.is_fixed_income:
            skipped.append(asset.ticker)
            continue
        if taxonomy.is_crypto:
            if _sync_crypto_position(db, user_id, asset, position):
                updated.append(asset.ticker)
            else:
                if _restore_suspicious_crypto_price(db, user_id, asset, position):
                    repaired.append(asset.ticker)
                skipped.append(asset.ticker)
            continue

        synced = sync_asset_market_data(db, asset, timeout=15.0)
        if synced:
            updated.append(asset.ticker)
        else:
            skipped.append(asset.ticker)
    db.commit()
    return {"updated": updated, "skipped": skipped, "repaired": repaired}


def _sync_crypto_position(db: Session, user_id: str, asset: Asset, position: dict) -> bool:
    from app.services.crypto import sync_crypto_asset

    if sync_crypto_asset(db, asset):
        return True
    return False


def _restore_suspicious_crypto_price(db: Session, user_id: str, asset: Asset, position: dict) -> bool:
    from app.services.crypto import restore_suspicious_crypto_mock_price

    return restore_suspicious_crypto_mock_price(db, user_id, asset, position)


def _average_transaction_price(db: Session, user_id: str, asset_id: str) -> Decimal | None:
    transactions = (
        db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id, Transaction.asset_id == asset_id)
            .order_by(Transaction.date.asc(), Transaction.created_at.asc())
        )
        .scalars()
        .all()
    )
    quantity = Decimal("0")
    cost = Decimal("0")
    for transaction in transactions:
        tx_type = (transaction.type or "").lower()
        tx_quantity = _decimal(transaction.quantity) or Decimal("0")
        tx_price = _decimal(transaction.price) or Decimal("0")
        tx_fees = _decimal(transaction.fees) or Decimal("0")
        if tx_quantity <= 0:
            continue
        if tx_type in {"buy", "compra"}:
            quantity += tx_quantity
            cost += tx_quantity * tx_price + tx_fees
        elif tx_type in {"sell", "venda"} and quantity > 0:
            sold_quantity = min(tx_quantity, quantity)
            average_cost = cost / quantity if quantity else Decimal("0")
            quantity -= sold_quantity
            cost -= average_cost * sold_quantity
    if quantity <= 0 or cost <= 0:
        return None
    return cost / quantity


def _asset_price(asset: Asset) -> Decimal:
    snapshot_price = asset.snapshot.price if asset.snapshot and asset.snapshot.price else None
    return Decimal(snapshot_price or asset.last_price or 0)
