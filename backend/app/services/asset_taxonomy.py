from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.models import Asset
from app.services.fixed_income import is_fixed_income_class


CLASS_ACOES_BRASIL = "Acoes Brasil"
CLASS_FIIS = "FIIs"
CLASS_ETFS_BRASIL = "ETFs Brasil"
CLASS_RENDA_FIXA_BRASIL = "Renda Fixa Brasil"
CLASS_CAIXA = "Caixa"
CLASS_ACOES_INTERNACIONAIS = "Acoes Internacionais"
CLASS_ETFS_INTERNACIONAIS = "ETFs Internacionais"
CLASS_REITS = "REITs"
CLASS_CRIPTO = "Cripto"
CLASS_TRADING = "Trading"
CLASS_COMMODITIES = "Commodities"
CLASS_OUTROS = "Outros"

BRAZIL_COUNTRIES = {"", "BR", "BRA", "BRASIL", "BRAZIL"}
BRAZIL_REGIONS = {"", "BRASIL", "BRAZIL", "AMERICA LATINA", "LATIN AMERICA"}
GLOBAL_MARKETS = {"NASDAQ", "NYSE", "AMEX", "ARCA", "LSE", "XETRA", "TSX", "TSE", "HKEX", "EURONEXT"}
CRYPTO_MARKETS = {"CRYPTO", "BINANCE", "COINBASE", "COINMARKETCAP", "COINGECKO"}
FIXED_INCOME_TERMS = (
    "renda fixa",
    "fixed income",
    "cdi",
    "rdb",
    "cdb",
    "tesouro",
    "lci",
    "lca",
    "debenture",
    "debenture",
    "resgate imediato",
    "liquidez diaria",
)


@dataclass(frozen=True)
class AssetTaxonomy:
    asset_class: str
    asset_subclass: str
    country: str
    region: str
    currency: str
    market: str
    exchange: str
    income_type: str
    risk_bucket: str
    liquidity_bucket: str
    strategy_bucket: str
    is_global_exposure: bool
    is_traditional_passive_income: bool
    is_fixed_income: bool
    is_crypto: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_position(position: dict | None = None, asset: Asset | None = None, external_account: dict | None = None) -> AssetTaxonomy:
    source = external_account or position or {}
    raw_class = _text(source.get("class") or getattr(asset, "asset_class", ""))
    raw_subclass = _text(source.get("subclass") or getattr(asset, "asset_subclass", "") or source.get("segment"))
    ticker = _text(source.get("ticker") or getattr(asset, "ticker", ""))
    name = _text(source.get("name") or getattr(asset, "name", ""))
    sector = _text(source.get("sector") or getattr(asset, "sector", ""))
    segment = _text(source.get("segment") or getattr(asset, "segment", ""))
    market = _text(source.get("market") or getattr(asset, "market", ""))
    exchange = _text(source.get("exchange") or getattr(asset, "exchange", ""))
    currency = _currency(source.get("currency") or getattr(asset, "trading_currency", "") or getattr(asset, "base_currency", "") or getattr(asset, "currency", ""))
    country = _country(source.get("country") or getattr(asset, "country_code", ""))
    region = _region(source.get("region") or getattr(asset, "region", ""))
    combined = " ".join([raw_class, raw_subclass, ticker, name, sector, segment, market, exchange]).lower()

    if external_account and _contains(raw_class, "trading"):
        return _taxonomy(CLASS_TRADING, "Operacoes", country or "BR", region or "Brasil", currency or "BRL", market, exchange, "trading_result", "high", "daily")

    if _is_fixed_income(raw_class, combined):
        subclass = _fixed_income_subclass(combined)
        liquidity = "daily" if any(term in combined for term in ("resgate imediato", "liquidez diaria", "liquidez diária")) else "contractual"
        return _taxonomy(CLASS_RENDA_FIXA_BRASIL, subclass, "BR", "Brasil", "BRL", market or "Balcao", exchange, "interest", "low", liquidity)

    if _contains(raw_class, "caixa") or "cash" in combined:
        return _taxonomy(CLASS_CAIXA, "Caixa", country or "BR", region or "Brasil", currency or "BRL", market, exchange, "interest", "very_low", "daily")

    if _is_crypto(raw_class, market, combined):
        return _taxonomy(CLASS_CRIPTO, raw_subclass or "Cryptoasset", country or "Global", region or "Global", currency or ticker or "USD", market or "Crypto", exchange, "none", "extreme", "variable")

    if _contains(raw_class, "commodity") or any(term in combined for term in ("ouro", "gold", "prata", "silver", "commodity")):
        return _taxonomy(CLASS_COMMODITIES, raw_subclass or "Commodity", country or "Global", region or "Global", currency or "USD", market, exchange, "none", "high", "variable")

    global_exposure = _is_global_exposure(currency, country, region, market, sector, raw_subclass)

    if _contains(raw_class, "reit"):
        return _taxonomy(CLASS_REITS, raw_subclass or "REIT", country or "US", region or "Global", currency or "USD", market, exchange, "dividend", "medium_high", "market")

    if _contains(raw_class, "fii") or "fundos imobili" in combined or ("imobili" in sector.lower() and _contains(raw_class, "fund")):
        return _taxonomy(CLASS_FIIS, raw_subclass or segment or "FII", "BR", "Brasil", "BRL", market or "B3", exchange, "real_estate_income", "medium", "market")

    if _contains(raw_class, "etf"):
        canonical = CLASS_ETFS_INTERNACIONAIS if global_exposure else CLASS_ETFS_BRASIL
        return _taxonomy(canonical, raw_subclass or "ETF", country or ("US" if global_exposure else "BR"), region or ("Global" if global_exposure else "Brasil"), currency or ("USD" if global_exposure else "BRL"), market, exchange, "distribution", "medium", "market")

    if _contains(raw_class, "bdr"):
        return _taxonomy(CLASS_ACOES_INTERNACIONAIS, "BDR", country or "US", region or "Global", currency or "BRL", market or "B3", exchange, "dividend", "medium_high", "market")

    if _contains_any(raw_class, ("acao", "acoes", "ação", "ações", "stock", "equity")) or global_exposure:
        canonical = CLASS_ACOES_INTERNACIONAIS if global_exposure else CLASS_ACOES_BRASIL
        return _taxonomy(canonical, raw_subclass or "Equity", country or ("US" if global_exposure else "BR"), region or ("Global" if global_exposure else "Brasil"), currency or ("USD" if global_exposure else "BRL"), market or ("B3" if not global_exposure else ""), exchange, "dividend", "medium_high", "market")

    return _taxonomy(CLASS_OUTROS, raw_subclass or raw_class or "Nao classificado", country or "BR", region or "Brasil", currency or "BRL", market, exchange, "unknown", "unknown", "unknown")


def canonical_class(position: dict | None = None, asset: Asset | None = None, external_account: dict | None = None) -> str:
    return classify_position(position, asset, external_account).asset_class


def strategy_bucket_for_class(asset_class: str) -> str:
    if asset_class == CLASS_ACOES_BRASIL:
        return "Acoes Brasil"
    if asset_class == CLASS_FIIS:
        return "FIIs"
    if asset_class == CLASS_ETFS_BRASIL:
        return "ETFs"
    if asset_class in {CLASS_ACOES_INTERNACIONAIS, CLASS_ETFS_INTERNACIONAIS, CLASS_REITS}:
        return "Global"
    if asset_class in {CLASS_RENDA_FIXA_BRASIL, CLASS_CAIXA}:
        return "Caixa/Renda Fixa"
    if asset_class == CLASS_CRIPTO:
        return "Cripto"
    if asset_class == CLASS_TRADING:
        return "Trading"
    return "Outros"


def is_traditional_passive_income_class(asset_class: str) -> bool:
    return asset_class in {
        CLASS_ACOES_BRASIL,
        CLASS_FIIS,
        CLASS_ETFS_BRASIL,
        CLASS_ACOES_INTERNACIONAIS,
        CLASS_ETFS_INTERNACIONAIS,
        CLASS_REITS,
    }


def is_global_class(asset_class: str) -> bool:
    return asset_class in {CLASS_ACOES_INTERNACIONAIS, CLASS_ETFS_INTERNACIONAIS, CLASS_REITS}


def _taxonomy(
    asset_class: str,
    asset_subclass: str,
    country: str,
    region: str,
    currency: str,
    market: str,
    exchange: str,
    income_type: str,
    risk_bucket: str,
    liquidity_bucket: str,
) -> AssetTaxonomy:
    return AssetTaxonomy(
        asset_class=asset_class,
        asset_subclass=asset_subclass,
        country=country or "BR",
        region=region or ("Global" if is_global_class(asset_class) else "Brasil"),
        currency=currency or ("USD" if is_global_class(asset_class) else "BRL"),
        market=market or "",
        exchange=exchange or "",
        income_type=income_type,
        risk_bucket=risk_bucket,
        liquidity_bucket=liquidity_bucket,
        strategy_bucket=strategy_bucket_for_class(asset_class),
        is_global_exposure=is_global_class(asset_class),
        is_traditional_passive_income=is_traditional_passive_income_class(asset_class),
        is_fixed_income=asset_class in {CLASS_RENDA_FIXA_BRASIL, CLASS_CAIXA},
        is_crypto=asset_class == CLASS_CRIPTO,
    )


def _is_fixed_income(raw_class: str, combined: str) -> bool:
    return is_fixed_income_class(raw_class) or any(term in combined for term in FIXED_INCOME_TERMS)


def _is_crypto(raw_class: str, market: str, combined: str) -> bool:
    return _contains_any(raw_class, ("cripto", "crypto")) or _text(market).upper() in CRYPTO_MARKETS or any(term in combined for term in ("bitcoin", "ethereum", "binance", "coin", "token"))


def _is_global_exposure(currency: str, country: str, region: str, market: str, sector: str, subclass: str) -> bool:
    if currency and currency != "BRL":
        return True
    if country.upper() not in BRAZIL_COUNTRIES:
        return True
    if region.upper() not in BRAZIL_REGIONS:
        return True
    if market.upper() in GLOBAL_MARKETS:
        return True
    text = f"{sector} {subclass}".lower()
    return any(term in text for term in ("exterior", "global", "eua", "internacional", "international"))


def _fixed_income_subclass(combined: str) -> str:
    if "rdb" in combined:
        return "RDB"
    if "cdb" in combined:
        return "CDB"
    if "tesouro" in combined:
        return "Tesouro"
    if "lci" in combined:
        return "LCI"
    if "lca" in combined:
        return "LCA"
    if "debenture" in combined or "debenture" in combined:
        return "Debenture"
    return "Renda fixa"


def _contains(value: str, term: str) -> bool:
    return term.lower() in value.lower()


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    normalized = value.lower()
    return any(term.lower() in normalized for term in terms)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _currency(value: Any) -> str:
    return _text(value).upper()


def _country(value: Any) -> str:
    return _text(value).upper()


def _region(value: Any) -> str:
    text = _text(value)
    return text or ""
