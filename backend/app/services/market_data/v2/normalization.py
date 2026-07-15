from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.market_data.v2.contracts import (
    DATA_TYPE_ASSET_SEARCH,
    DATA_TYPE_DIVIDENDS,
    DATA_TYPE_FUNDAMENTALS,
    DATA_TYPE_FX_RATE,
    DATA_TYPE_PRICE_HISTORY,
    DATA_TYPE_QUOTE,
    MarketDataRequest,
    NormalizedMarketData,
)


def safe_float(value: Any, default: float = 0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_percent(value: Any) -> float:
    number = safe_float(value)
    if -1 < number < 1 and number != 0:
        return number * 100
    return number


def normalize_payload(
    *,
    data_type: str,
    provider: str,
    request: MarketDataRequest,
    payload: dict[str, Any],
    currency: str = "BRL",
    quality_score: float = 80,
    warnings: tuple[str, ...] = (),
) -> NormalizedMarketData:
    return NormalizedMarketData(
        asset_id=request.asset_id,
        data_type=data_type,
        provider=provider,
        source_symbol=request.normalized_symbol,
        currency=(currency or request.currency or "BRL").upper(),
        as_of=datetime.now(timezone.utc),
        payload=payload,
        quality_score=quality_score,
        warnings=warnings,
    )


def normalize_quote(provider: str, request: MarketDataRequest, *, price: Any, currency: str = "BRL", **extra: Any) -> NormalizedMarketData:
    normalized_price = safe_float(price)
    return normalize_payload(
        data_type=DATA_TYPE_QUOTE,
        provider=provider,
        request=request,
        currency=currency,
        quality_score=92 if normalized_price > 0 else 35,
        warnings=() if normalized_price > 0 else ("missing_price",),
        payload={"price": normalized_price, "regularMarketPrice": normalized_price, "currency": currency, **extra},
    )


def normalize_fundamentals(provider: str, request: MarketDataRequest, *, raw: dict[str, Any], currency: str = "BRL") -> NormalizedMarketData:
    payload = {
        "price": safe_float(raw.get("regularMarketPrice") or raw.get("price")),
        "dividend_yield": normalize_percent(raw.get("dividendYield") or raw.get("dividend_yield")),
        "payout": normalize_percent(raw.get("payoutRatio") or raw.get("payout")),
        "pe_ratio": safe_float(raw.get("priceEarnings") or raw.get("trailingPE") or raw.get("pe_ratio")),
        "pvp": safe_float(raw.get("priceToBook") or raw.get("pvp")),
        "ev_ebitda": safe_float(raw.get("enterpriseToEbitda") or raw.get("evEbitda") or raw.get("ev_ebitda")),
        "revenue_growth": normalize_percent(raw.get("revenueGrowth") or raw.get("revenue_growth")),
        "profit_growth": normalize_percent(raw.get("earningsGrowth") or raw.get("profit_growth")),
        "net_margin": normalize_percent(raw.get("profitMargins") or raw.get("net_margin")),
        "roe": normalize_percent(raw.get("returnOnEquity") or raw.get("roe")),
        "roic": normalize_percent(raw.get("roic")),
        "debt_to_ebitda": safe_float(raw.get("debtToEbitda") or raw.get("debt_to_ebitda")),
        "revenue": safe_float(raw.get("totalRevenue") or raw.get("revenue")),
        "profit": safe_float(raw.get("netIncome") or raw.get("profit")),
        "market_value": safe_float(raw.get("marketCap") or raw.get("market_value")),
    }
    populated = sum(1 for value in payload.values() if value not in (0, 0.0))
    return normalize_payload(
        data_type=DATA_TYPE_FUNDAMENTALS,
        provider=provider,
        request=request,
        currency=currency,
        quality_score=min(95, 45 + populated * 6),
        warnings=() if populated else ("partial_fundamentals",),
        payload=payload,
    )


def normalize_dividends(provider: str, request: MarketDataRequest, dividends: list[dict[str, Any]]) -> NormalizedMarketData:
    return normalize_payload(
        data_type=DATA_TYPE_DIVIDENDS,
        provider=provider,
        request=request,
        payload={"dividends": dividends},
        quality_score=70 if dividends else 45,
        warnings=() if dividends else ("empty_dividend_history",),
    )


def normalize_price_history(provider: str, request: MarketDataRequest, prices: list[dict[str, Any]]) -> NormalizedMarketData:
    return normalize_payload(
        data_type=DATA_TYPE_PRICE_HISTORY,
        provider=provider,
        request=request,
        payload={"prices": prices, "interval": request.interval},
        quality_score=74 if prices else 40,
        warnings=() if prices else ("empty_price_history",),
    )


def normalize_fx_rate(provider: str, request: MarketDataRequest, *, rate: Any) -> NormalizedMarketData:
    base = (request.base_currency or request.symbol).upper()
    quote = (request.quote_currency or request.currency or "BRL").upper()
    return normalize_payload(
        data_type=DATA_TYPE_FX_RATE,
        provider=provider,
        request=request,
        currency=quote,
        payload={"base_currency": base, "quote_currency": quote, "rate": safe_float(rate)},
        quality_score=86,
    )


def normalize_asset_search(provider: str, request: MarketDataRequest, results: list[dict[str, Any]]) -> NormalizedMarketData:
    return normalize_payload(
        data_type=DATA_TYPE_ASSET_SEARCH,
        provider=provider,
        request=request,
        payload={"results": results},
        quality_score=72 if results else 40,
        warnings=() if results else ("empty_asset_search",),
    )
