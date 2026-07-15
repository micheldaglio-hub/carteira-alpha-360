from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date
from math import isfinite
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, Dividend
from app.services.income import add_income_to_breakdown, empty_income_breakdown, normalize_income_type


def apply_total_return_overlay(
    db: Session,
    user_id: str,
    positions: list[dict],
    rows: list[dict],
    start_date: date,
    end_date: date,
) -> tuple[list[dict], dict]:
    """Overlay internally registered dividends/JCP/FII income on the price backtest.

    The price backtest remains the base source for capital appreciation. This
    engine adds only cash distributions already registered in the user's ledger,
    so Total Return is auditable and never inferred from generic yield.
    """

    enriched_rows = deepcopy(rows)
    if not enriched_rows:
        return enriched_rows, _empty_report()

    assets = _assets_by_id(db, positions)
    dividends = _dividends_in_range(db, user_id, start_date, end_date)
    income_by_row: dict[int, dict] = defaultdict(_new_month_income)
    income_by_asset: dict[str, dict] = defaultdict(_new_asset_income)

    for dividend in dividends:
        asset = assets.get(dividend.asset_id) or db.get(Asset, dividend.asset_id)
        asset_class = asset.asset_class if asset else ""
        row_index = _row_index_for_income(enriched_rows, dividend.date, start_date)
        amount = _float(dividend.total_amount)
        classification = normalize_income_type(dividend.source, asset_class)
        bucket = _bucket_for_asset_class(asset_class)

        add_income_to_breakdown(income_by_row[row_index]["breakdown"], amount, dividend.source, asset_class)
        income_by_row[row_index]["total"] += amount
        income_by_row[row_index][bucket] += amount
        income_by_row[row_index]["events"] += 1

        asset_key = asset.ticker if asset else dividend.asset_id
        income_by_asset[asset_key]["ticker"] = asset_key
        income_by_asset[asset_key]["name"] = asset.name if asset else asset_key
        income_by_asset[asset_key]["assetClass"] = asset_class
        income_by_asset[asset_key]["total"] += amount
        income_by_asset[asset_key][classification.key] += amount
        income_by_asset[asset_key]["events"] += 1

    for index, row in enumerate(enriched_rows):
        month_income = income_by_row.get(index, _new_month_income())
        row["incomeTotal"] = round(month_income["total"], 2)
        row["incomeStocks"] = round(month_income["stocks"], 2)
        row["incomeCrypto"] = round(month_income["crypto"], 2)
        row["incomeFixedIncome"] = round(month_income["fixedIncome"], 2)
        row["incomeBreakdown"] = _rounded_breakdown(month_income["breakdown"])
        row["incomeEvents"] = int(month_income["events"])
        row["monthlyTotalReturnPct"] = _return_with_income(
            row.get("monthlyReturnPct"),
            month_income["total"],
            row.get("performanceBaseTotal") or row.get("capitalBaseValue") or row.get("baselineValue"),
        )
        row["riskAssetsTotalReturnPct"] = _return_with_income(
            row.get("riskAssetsReturnPct"),
            month_income["stocks"] + month_income["crypto"],
            row.get("performanceBaseRiskAssets") or row.get("riskAssetsValue"),
        )
        row["stocksTotalReturnPct"] = _return_with_income(
            row.get("stocksReturnPct"),
            month_income["stocks"],
            row.get("performanceBaseStocks") or row.get("stocksValue"),
        )
        row["cryptoTotalReturnPct"] = _return_with_income(
            row.get("cryptoReturnPct"),
            month_income["crypto"],
            row.get("performanceBaseCrypto") or row.get("cryptoValue"),
        )
        row["fixedIncomeTotalReturnPct"] = _return_with_income(
            row.get("fixedIncomeReturnPct"),
            month_income["fixedIncome"],
            row.get("performanceBaseFixedIncome") or row.get("fixedIncomeValue"),
        )

    report = _build_report(enriched_rows, income_by_asset)
    return enriched_rows, report


def _build_report(rows: list[dict], income_by_asset: dict[str, dict]) -> dict:
    performance_rows = rows[1:] if len(rows) > 1 else rows
    breakdown = empty_income_breakdown()
    for row in rows:
        for key, value in (row.get("incomeBreakdown") or {}).items():
            if key in breakdown:
                breakdown[key] = round(_float(breakdown[key]) + _float(value), 2)

    monthly_total = [_float(row.get("monthlyTotalReturnPct")) for row in performance_rows]
    monthly_risk = [_float(row.get("riskAssetsTotalReturnPct")) for row in performance_rows]
    monthly_stocks = [_float(row.get("stocksTotalReturnPct")) for row in performance_rows]
    monthly_crypto = [_float(row.get("cryptoTotalReturnPct")) for row in performance_rows]
    monthly_fixed = [_float(row.get("fixedIncomeTotalReturnPct")) for row in performance_rows]

    return {
        "status": "operational",
        "title": "Total Return Engine",
        "mode": "internal_income_ledger",
        "incomeTotal": round(_float(breakdown.get("total_proceeds")), 2),
        "breakdown": _rounded_breakdown(breakdown),
        "assetIncome": sorted(
            [_round_asset_income(item) for item in income_by_asset.values()],
            key=lambda item: item["total"],
            reverse=True,
        ),
        "returns": {
            "totalReturnWithIncomePct": _compound_return(monthly_total),
            "riskAssetsReturnWithIncomePct": _compound_return(monthly_risk),
            "stocksReturnWithIncomePct": _compound_return(monthly_stocks),
            "cryptoReturnWithIncomePct": _compound_return(monthly_crypto),
            "fixedIncomeReturnWithIncomePct": _compound_return(monthly_fixed),
            "averageMonthlyTotalReturnWithIncomePct": round(mean(monthly_total), 2) if monthly_total else 0,
            "averageMonthlyStocksReturnWithIncomePct": round(mean(monthly_stocks), 2) if monthly_stocks else 0,
        },
        "plainLanguage": [
            "Retorno de preco mede apenas valorizacao ou queda dos ativos.",
            "Total Return soma retorno de preco com proventos, JCP e rendimentos registrados no livro interno.",
            "Quando nao houver provento cadastrado no periodo, o Total Return fica igual ou muito proximo do retorno de preco.",
        ],
        "limitations": [
            "Neste passo, proventos historicos entram somente quando existem no cadastro interno do usuario.",
            "Dividendos/JCP antigos de provider externo ainda precisam passar pelo Knowledge Engine antes de alterar o backtest.",
            "Renda fixa CDI ja aparece no valor atual estimado; este motor nao duplica juros de renda fixa como provento.",
        ],
    }


def _assets_by_id(db: Session, positions: list[dict]) -> dict[str, Asset]:
    ids = [position.get("assetId") for position in positions if position.get("assetId")]
    if not ids:
        return {}
    rows = db.execute(select(Asset).where(Asset.id.in_(ids))).scalars().all()
    return {asset.id: asset for asset in rows}


def _dividends_in_range(db: Session, user_id: str, start_date: date, end_date: date) -> list[Dividend]:
    return (
        db.execute(
            select(Dividend).where(
                Dividend.user_id == user_id,
                Dividend.date >= start_date,
                Dividend.date <= end_date,
            )
        )
        .scalars()
        .all()
    )


def _row_index_for_income(rows: list[dict], income_date: date, start_date: date) -> int:
    previous = start_date
    for index, row in enumerate(rows):
        row_date = _parse_row_date(row)
        if index == 0:
            if income_date <= row_date:
                return index
            previous = row_date
            continue
        if previous < income_date <= row_date:
            return index
        previous = row_date
    return max(len(rows) - 1, 0)


def _parse_row_date(row: dict) -> date:
    raw = str(row.get("date") or "")
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return date.today()


def _new_month_income() -> dict:
    return {
        "total": 0.0,
        "stocks": 0.0,
        "crypto": 0.0,
        "fixedIncome": 0.0,
        "events": 0,
        "breakdown": empty_income_breakdown(),
    }


def _new_asset_income() -> dict:
    return {
        "ticker": "",
        "name": "",
        "assetClass": "",
        "total": 0.0,
        "dividend": 0.0,
        "jcp": 0.0,
        "fii_income": 0.0,
        "other_income": 0.0,
        "events": 0,
    }


def _bucket_for_asset_class(asset_class: str) -> str:
    normalized = str(asset_class or "").lower()
    if "cripto" in normalized or "crypto" in normalized:
        return "crypto"
    if "renda fixa" in normalized or "fixed income" in normalized or "cdb" in normalized or "rdb" in normalized:
        return "fixedIncome"
    return "stocks"


def _return_with_income(price_return_pct: Any, income: float, base: Any) -> float:
    base_value = _float(base)
    income_return = (_float(income) / base_value * 100) if base_value > 0 else 0.0
    return round(_float(price_return_pct) + income_return, 2)


def _compound_return(monthly_returns: list[float]) -> float:
    factor = 1.0
    for value in monthly_returns:
        factor *= 1 + _float(value) / 100
    return round((factor - 1) * 100, 2)


def _rounded_breakdown(breakdown: dict) -> dict:
    return {key: round(_float(value), 2) for key, value in breakdown.items()}


def _round_asset_income(item: dict) -> dict:
    return {
        **item,
        "total": round(_float(item.get("total")), 2),
        "dividend": round(_float(item.get("dividend")), 2),
        "jcp": round(_float(item.get("jcp")), 2),
        "fii_income": round(_float(item.get("fii_income")), 2),
        "other_income": round(_float(item.get("other_income")), 2),
    }


def _empty_report() -> dict:
    return {
        "status": "empty",
        "title": "Total Return Engine",
        "mode": "internal_income_ledger",
        "incomeTotal": 0,
        "breakdown": empty_income_breakdown(),
        "assetIncome": [],
        "returns": {},
        "plainLanguage": [],
        "limitations": [],
    }


def _float(value: Any) -> float:
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0.0
    except Exception:
        return 0.0
