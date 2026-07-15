from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset
from app.services.asset_taxonomy import (
    CLASS_ACOES_BRASIL,
    CLASS_CRIPTO,
    CLASS_RENDA_FIXA_BRASIL,
    CLASS_TRADING,
    classify_position,
    is_global_class,
)


def build_portfolio_snapshot(
    positions: list[dict],
    *,
    external_accounts: list[dict] | None = None,
    assets_by_id: dict[str, Asset] | None = None,
) -> dict:
    assets_by_id = assets_by_id or {}
    classified_positions: list[dict] = []
    by_class: dict[str, float] = defaultdict(float)
    by_strategy_bucket: dict[str, float] = defaultdict(float)
    by_country: dict[str, float] = defaultdict(float)
    by_region: dict[str, float] = defaultdict(float)
    by_currency: dict[str, float] = defaultdict(float)
    by_sector: dict[str, float] = defaultdict(float)
    by_asset: dict[str, float] = defaultdict(float)
    totals = {
        "currentValue": 0.0,
        "investedValue": 0.0,
        "pnl": 0.0,
        "portfolioCurrentValue": 0.0,
        "portfolioInvestedValue": 0.0,
        "externalCurrentValue": 0.0,
        "externalInvestedValue": 0.0,
    }
    exposures = {
        "brazilValue": 0.0,
        "globalValue": 0.0,
        "cryptoValue": 0.0,
        "tradingValue": 0.0,
        "fixedIncomeValue": 0.0,
        "traditionalPassiveIncomeValue": 0.0,
    }
    recurring_income = {
        "projectedProceedsMonthly": 0.0,
        "projectedFixedIncomeMonthly": 0.0,
        "projectedTradingMonthly": 0.0,
        "projectedTotalMonthly": 0.0,
    }

    for position in positions:
        asset = assets_by_id.get(str(position.get("assetId")))
        taxonomy = classify_position(position, asset)
        current_value = _number(position.get("currentValue"))
        invested_value = _number(position.get("investedValue"))
        pnl = current_value - invested_value
        totals["currentValue"] += current_value
        totals["investedValue"] += invested_value
        totals["pnl"] += pnl
        totals["portfolioCurrentValue"] += current_value
        totals["portfolioInvestedValue"] += invested_value
        _add_allocations(
            by_class=by_class,
            by_strategy_bucket=by_strategy_bucket,
            by_country=by_country,
            by_region=by_region,
            by_currency=by_currency,
            by_sector=by_sector,
            by_asset=by_asset,
            taxonomy=taxonomy,
            sector=str(position.get("sector") or "Nao classificado"),
            asset_name=str(position.get("ticker") or position.get("name") or "Ativo"),
            value=current_value,
        )
        _add_exposures(exposures, taxonomy, current_value)
        if taxonomy.is_fixed_income:
            recurring_income["projectedFixedIncomeMonthly"] += _fixed_income_monthly_income(position)
        elif taxonomy.is_traditional_passive_income:
            recurring_income["projectedProceedsMonthly"] += current_value * _number(position.get("dividendYieldOnAvg")) / 100 / 12
        classified = dict(position)
        classified["canonicalClass"] = taxonomy.asset_class
        classified["strategyBucket"] = taxonomy.strategy_bucket
        classified["taxonomy"] = taxonomy.to_dict()
        classified_positions.append(classified)

    for account in external_accounts or []:
        taxonomy = classify_position(external_account=account)
        current_value = _number(account.get("currentValue"))
        invested_value = _number(account.get("investedValue"))
        pnl = _number(account.get("pnl"), current_value - invested_value)
        totals["currentValue"] += current_value
        totals["investedValue"] += invested_value
        totals["pnl"] += pnl
        totals["externalCurrentValue"] += current_value
        totals["externalInvestedValue"] += invested_value
        _add_allocations(
            by_class=by_class,
            by_strategy_bucket=by_strategy_bucket,
            by_country=by_country,
            by_region=by_region,
            by_currency=by_currency,
            by_sector=by_sector,
            by_asset=by_asset,
            taxonomy=taxonomy,
            sector=str(account.get("sector") or "Estrategias"),
            asset_name=str(account.get("ticker") or account.get("name") or "Conta externa"),
            value=current_value,
        )
        _add_exposures(exposures, taxonomy, current_value)
        recurring_income["projectedTradingMonthly"] += 0.0
        classified_positions.append(
            {
                **account,
                "canonicalClass": taxonomy.asset_class,
                "strategyBucket": taxonomy.strategy_bucket,
                "taxonomy": taxonomy.to_dict(),
                "isExternal": True,
            }
        )

    total_current = totals["currentValue"]
    for key in list(exposures):
        pct_key = key.replace("Value", "Pct")
        exposures[pct_key] = _round(exposures[key] / total_current * 100 if total_current else 0.0)
        exposures[key] = _round(exposures[key])

    recurring_income["projectedTotalMonthly"] = (
        recurring_income["projectedProceedsMonthly"]
        + recurring_income["projectedFixedIncomeMonthly"]
        + recurring_income["projectedTradingMonthly"]
    )

    allocations = {
        "byClass": _to_rows(by_class),
        "byStrategyBucket": _to_rows(by_strategy_bucket),
        "byCountry": _to_rows(by_country),
        "byRegion": _to_rows(by_region),
        "byCurrency": _to_rows(by_currency),
        "bySector": _to_rows(by_sector),
        "byAsset": _to_rows(by_asset),
    }
    totals = {key: _round(value) for key, value in totals.items()}
    totals["pnlPct"] = _round(totals["pnl"] / totals["investedValue"] * 100 if totals["investedValue"] else 0.0)
    consistency = _consistency(allocations, totals["currentValue"])
    return {
        "totals": totals,
        "allocations": allocations,
        "exposures": exposures,
        "recurringIncome": {key: _round(value) for key, value in recurring_income.items()},
        "positions": classified_positions,
        "largest": {
            "class": _largest(allocations["byClass"]),
            "asset": _largest(allocations["byAsset"]),
            "country": _largest(allocations["byCountry"]),
            "currency": _largest(allocations["byCurrency"]),
        },
        "consistency": consistency,
        "calculation": "portfolio_aggregation_engine_v1",
    }


def build_user_portfolio_snapshot(db: Session, user_id: str, *, include_external: bool = True) -> dict:
    from app.services.portfolio import get_positions
    from app.services.trading_desk_integration import get_trading_desk_summary

    positions = get_positions(db, user_id)
    assets = _load_assets(db, positions)
    external_accounts = []
    if include_external:
        trading = get_trading_desk_summary()
        if trading.get("connected"):
            external_accounts.append(
                {
                    "ticker": "Trading Desk EV+",
                    "name": "Trading Desk EV+",
                    "class": CLASS_TRADING,
                    "sector": "Estrategias",
                    "currentValue": _number(trading.get("currentBalance")),
                    "investedValue": _number(trading.get("initialCapital")),
                    "pnl": _number(trading.get("totalPnl")),
                    "currency": "BRL",
                    "country": "BR",
                }
            )
    return build_portfolio_snapshot(positions, external_accounts=external_accounts, assets_by_id=assets)


def _load_assets(db: Session, positions: list[dict]) -> dict[str, Asset]:
    ids = [str(position.get("assetId")) for position in positions if position.get("assetId")]
    if not ids:
        return {}
    rows = db.execute(select(Asset).where(Asset.id.in_(ids))).scalars().all()
    return {item.id: item for item in rows}


def _add_allocations(
    *,
    by_class: dict[str, float],
    by_strategy_bucket: dict[str, float],
    by_country: dict[str, float],
    by_region: dict[str, float],
    by_currency: dict[str, float],
    by_sector: dict[str, float],
    by_asset: dict[str, float],
    taxonomy,
    sector: str,
    asset_name: str,
    value: float,
) -> None:
    if value <= 0:
        return
    by_class[taxonomy.asset_class] += value
    by_strategy_bucket[taxonomy.strategy_bucket] += value
    by_country[taxonomy.country or "BR"] += value
    by_region[taxonomy.region or "Brasil"] += value
    by_currency[taxonomy.currency or "BRL"] += value
    by_sector[sector or "Nao classificado"] += value
    by_asset[asset_name or "Ativo"] += value


def _add_exposures(exposures: dict[str, float], taxonomy, value: float) -> None:
    if taxonomy.asset_class in {CLASS_ACOES_BRASIL, CLASS_RENDA_FIXA_BRASIL} or taxonomy.country == "BR":
        exposures["brazilValue"] += value
    if taxonomy.is_global_exposure or is_global_class(taxonomy.asset_class):
        exposures["globalValue"] += value
    if taxonomy.asset_class == CLASS_CRIPTO:
        exposures["cryptoValue"] += value
    if taxonomy.asset_class == CLASS_TRADING:
        exposures["tradingValue"] += value
    if taxonomy.is_fixed_income:
        exposures["fixedIncomeValue"] += value
    if taxonomy.is_traditional_passive_income:
        exposures["traditionalPassiveIncomeValue"] += value


def _to_rows(source: dict[str, float]) -> list[dict]:
    total = sum(source.values())
    return [
        {"name": key, "value": _round(value), "weight": _round(value / total * 100 if total else 0.0)}
        for key, value in sorted(source.items(), key=lambda item: item[1], reverse=True)
    ]


def _largest(rows: list[dict]) -> dict:
    return rows[0] if rows else {"name": "", "value": 0.0, "weight": 0.0}


def _consistency(allocations: dict, total_current: float) -> dict:
    class_value_sum = sum(_number(row.get("value")) for row in allocations["byClass"])
    class_weight_sum = sum(_number(row.get("weight")) for row in allocations["byClass"])
    return {
        "classValueSum": _round(class_value_sum),
        "classWeightSum": _round(class_weight_sum),
        "totalCurrentValue": _round(total_current),
        "difference": _round(class_value_sum - total_current),
        "isBalanced": abs(class_value_sum - total_current) <= 0.03 and (abs(class_weight_sum - 100) <= 0.08 or total_current == 0),
    }


def _fixed_income_monthly_income(position: dict) -> float:
    current_value = _number(position.get("currentValue"))
    fixed_info = position.get("fixedIncome") or {}
    if current_value <= 0:
        return 0.0
    cdi_percent = _number(fixed_info.get("cdiPercent"), 100.0)
    daily_rate_pct = _number(fixed_info.get("dailyRatePct"), 0.047)
    daily_factor = 1 + ((daily_rate_pct / 100) * (cdi_percent / 100))
    return current_value * (daily_factor**21 - 1)


def _number(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _round(value: float, digits: int = 2) -> float:
    return round(float(value or 0.0), digits)
