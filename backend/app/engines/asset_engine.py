from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, AssetIdentifier


@dataclass(frozen=True)
class AssetEngineMetadata:
    universal_symbol: str
    asset_subclass: str
    country_code: str
    region: str
    market: str
    exchange: str
    base_currency: str
    trading_currency: str
    industry: str
    status: str = "active"


def normalize_asset_symbol(value: str) -> str:
    return (value or "").strip().upper()


def infer_asset_engine_metadata(
    *,
    ticker: str,
    asset_class: str,
    sector: str = "",
    segment: str = "",
    currency: str = "BRL",
) -> AssetEngineMetadata:
    symbol = normalize_asset_symbol(ticker)
    normalized_class = (asset_class or "").strip().lower()
    normalized_currency = normalize_asset_symbol(currency or "BRL") or "BRL"
    industry = (segment or sector or "").strip()

    if normalized_class in {"cripto", "crypto"}:
        return AssetEngineMetadata(
            universal_symbol=f"CRYPTO:{symbol}",
            asset_subclass=segment or "Cryptoasset",
            country_code="",
            region="Global",
            market="Crypto",
            exchange="",
            base_currency=symbol,
            trading_currency=normalized_currency,
            industry=industry or "Crypto",
        )

    if "renda fixa" in normalized_class or normalized_class in {"fixed income", "cdb", "rdb", "tesouro"}:
        return AssetEngineMetadata(
            universal_symbol=f"BR:FIXED_INCOME:{symbol}",
            asset_subclass=segment or "Brazilian Fixed Income",
            country_code="BR",
            region="Latin America",
            market="Fixed Income",
            exchange="",
            base_currency=normalized_currency,
            trading_currency=normalized_currency,
            industry=industry or "Renda fixa",
        )

    if "fii" in normalized_class:
        asset_subclass = "Brazilian Real Estate Fund"
    elif "etf" in normalized_class:
        asset_subclass = "Brazilian Listed ETF"
    elif normalized_class in {"acoes", "acao", "equity", "stock"}:
        asset_subclass = "Brazilian Equity"
    else:
        asset_subclass = asset_class or "Unclassified Asset"

    return AssetEngineMetadata(
        universal_symbol=f"BR:B3:{symbol}",
        asset_subclass=asset_subclass,
        country_code="BR",
        region="Latin America",
        market="B3",
        exchange="B3",
        base_currency=normalized_currency,
        trading_currency=normalized_currency,
        industry=industry,
    )


def apply_asset_engine_defaults(asset: Asset, *, force: bool = False) -> Asset:
    metadata = infer_asset_engine_metadata(
        ticker=asset.ticker,
        asset_class=asset.asset_class,
        sector=asset.sector,
        segment=asset.segment,
        currency=asset.currency,
    )

    for field, value in metadata.__dict__.items():
        if force or not getattr(asset, field, None):
            setattr(asset, field, value)

    if force or not asset.industry:
        asset.industry = metadata.industry
    if force or not asset.status:
        asset.status = "active"
    return asset


def ensure_primary_identifiers(db: Session, asset: Asset) -> None:
    if not asset.id:
        db.flush()

    candidates = [
        ("universal_symbol", asset.universal_symbol or "", "", asset.market or "", True),
        ("ticker", normalize_asset_symbol(asset.ticker), "", asset.market or "", False),
    ]
    provider_symbol = normalize_asset_symbol(asset.provider_symbol or "")
    if provider_symbol and provider_symbol != normalize_asset_symbol(asset.ticker):
        candidates.append(("provider_symbol", provider_symbol, "default", asset.market or "", False))

    existing = {
        (row.identifier_type, row.identifier_value, row.provider, row.market)
        for row in db.execute(select(AssetIdentifier).where(AssetIdentifier.asset_id == asset.id)).scalars().all()
    }

    for identifier_type, identifier_value, provider, market, is_primary in candidates:
        if not identifier_value:
            continue
        key = (identifier_type, identifier_value, provider, market)
        if key in existing:
            continue
        db.add(
            AssetIdentifier(
                asset_id=asset.id,
                identifier_type=identifier_type,
                identifier_value=identifier_value,
                provider=provider,
                market=market,
                is_primary=is_primary,
            )
        )


def ensure_asset_engine_metadata(db: Session, asset: Asset, *, force: bool = False) -> Asset:
    apply_asset_engine_defaults(asset, force=force)
    db.add(asset)
    db.flush()
    ensure_primary_identifiers(db, asset)
    return asset


def decimal_100() -> Decimal:
    return Decimal("100.0000")
