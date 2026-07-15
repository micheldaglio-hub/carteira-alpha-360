from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from math import isfinite

from sqlalchemy.orm import Session

from app.models import Asset
from app.services.data_lineage import record_evidence_batch
from app.services.data_confidence_engine import build_data_confidence_audit
from app.services.market_data.v2.contracts import DATA_TYPE_PRICE_HISTORY, MarketDataRequest, MarketDataUnavailable
from app.services.market_data.v2.engine import MarketDataEngine
from app.services.fixed_income import is_fixed_income_class
from app.services.portfolio import get_positions
from app.services.projection_premises import get_dashboard_projection_premises
from app.services.total_return_engine import apply_total_return_overlay


def get_current_portfolio_backtest(db: Session, user_id: str, start_date: date, end_date: date) -> dict:
    start, end = _normalize_range(start_date, end_date)
    positions = get_positions(db, user_id)
    histories: dict[str, list[dict]] = {}
    sources: dict[str, str] = {}
    warnings: list[str] = []

    engine = MarketDataEngine(db=db)
    for position in positions:
        asset = db.get(Asset, position["assetId"])
        if asset is None:
            continue
        if _is_fixed_income(position):
            histories[position["assetId"]] = []
            sources[position["ticker"]] = "fixed_income_current_value"
            continue
        try:
            request = MarketDataRequest(
                symbol=asset.ticker,
                asset_id=asset.id,
                provider_symbol=asset.provider_symbol or asset.ticker,
                market=asset.market or ("Crypto" if _is_crypto(position) else "B3"),
                asset_class=asset.asset_class,
                currency=asset.currency or "BRL",
                start_date=start,
                end_date=end,
                interval="1day",
            )
            record, prices = _first_real_history(engine, request)
            histories[position["assetId"]] = prices
            sources[position["ticker"]] = record.provider if record and prices else "fallback_current_price"
            if not prices:
                warnings.append(f"{position['ticker']} sem historico real suficiente; usado preco atual como fallback.")
        except (MarketDataUnavailable, Exception):
            histories[position["assetId"]] = []
            sources[position["ticker"]] = "fallback_current_price"
            warnings.append(f"{position['ticker']} sem historico real suficiente; usado preco atual como fallback.")

    try:
        db.commit()
    except Exception:
        db.rollback()

    premises = get_dashboard_projection_premises(db, user_id) or {}
    monthly_contribution = _float(premises.get("monthly_contribution"))
    baseline_by_asset = {position["assetId"]: _float(position.get("currentValue")) for position in positions}
    rows = build_current_portfolio_backtest_series(
        positions,
        histories,
        start,
        end,
        baseline_by_asset=baseline_by_asset,
        monthly_contribution=monthly_contribution,
    )
    rows, total_return_report = apply_total_return_overlay(db, user_id, positions, rows, start, end)
    summary = _summary(rows, positions, sources, warnings, monthly_contribution)
    _merge_total_return_summary(summary, total_return_report)
    data_confidence_audit = build_data_confidence_audit(
        db,
        user_id,
        backtest_sources=sources,
        backtest_warnings=warnings,
    )
    lineage = _record_backtest_lineage(db, user_id, start, end, summary, data_confidence_audit, sources, warnings)
    return {
        "mode": "current_holdings_retroactive",
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "summary": summary,
        "rows": rows,
        "totalReturn": total_return_report,
        "dataConfidence": data_confidence_audit,
        "dataLineage": lineage,
        "sources": sources,
        "warnings": warnings[:8],
        "notes": [
            "Simulacao usa o valor atual real de cada ativo como ponto de partida e aplica sua variacao historica individual.",
            "Aporte mensal vem das premissas salvas na Visao Geral e e distribuido proporcionalmente entre os ativos simulados.",
            "Retorno total e calculado por performance encadeada dos ativos, sem contar aporte como lucro.",
            "Total Return soma retorno de preco com dividendos, JCP e rendimentos cadastrados no livro interno.",
            "Renda fixa fica separada de acoes e cripto; no backtest retroativo inicial ela usa valor atual como ancora, sem curva historica detalhada de CDI.",
            "Historico de proventos vindo de provider externo ainda precisa passar pelo Knowledge Engine antes de compor a serie historica.",
            "Quando algum provider nao entrega historico, o ativo fica com preco atual como fallback para nao quebrar a simulacao.",
        ],
    }


def _record_backtest_lineage(
    db: Session,
    user_id: str,
    start: date,
    end: date,
    summary: dict,
    data_confidence_audit: dict,
    sources: dict[str, str],
    warnings: list[str],
) -> dict:
    trace_id = f"backtest:{user_id}:{start.isoformat()}:{end.isoformat()}"
    confidence = _float(data_confidence_audit.get("overallScore"))
    source_type = "fallback" if summary.get("fallbackAssets", 0) else "formula"
    status = "fallback" if source_type == "fallback" else "ok"
    fields = [
        ("initialValue", "BRL"),
        ("finalValue", "BRL"),
        ("totalReturnPct", "%"),
        ("stocksReturnPct", "%"),
        ("cryptoReturnPct", "%"),
        ("fixedIncomeReturnPct", "%"),
        ("totalReturnWithIncomePct", "%"),
        ("incomeTotal", "BRL"),
    ]
    rows = []
    for field_name, unit in fields:
        if field_name not in summary:
            continue
        rows.append(
            {
                "domain": "portfolio_backtest",
                "field_name": field_name,
                "user_id": user_id,
                "value_numeric": summary.get(field_name),
                "currency": "BRL" if unit == "BRL" else "",
                "unit": unit,
                "provider": "portfolio_backtest_engine",
                "source_type": source_type,
                "source_ref": "app.services.portfolio_backtest.get_current_portfolio_backtest",
                "formula_name": f"portfolio_backtest.{field_name}",
                "input_payload": {
                    "startDate": start.isoformat(),
                    "endDate": end.isoformat(),
                    "sources": sources,
                    "warningCount": len(warnings),
                    "monthlyContribution": summary.get("monthlyContribution"),
                },
                "confidence": confidence,
                "quality_score": confidence,
                "status": status,
                "trace_id": trace_id,
                "metadata": {"dataConfidence": data_confidence_audit.get("classification"), "warnings": warnings[:8]},
            }
        )
    evidence = record_evidence_batch(db, rows) if rows else []
    try:
        db.commit()
    except Exception:
        db.rollback()
        return {"status": "not_persisted", "traceId": trace_id, "evidenceCount": 0}
    return {
        "status": "recorded",
        "traceId": trace_id,
        "evidenceCount": len(evidence),
        "confidence": confidence,
        "classification": data_confidence_audit.get("classification", ""),
    }


def _first_real_history(engine: MarketDataEngine, request: MarketDataRequest):
    records = engine.collect(DATA_TYPE_PRICE_HISTORY, request, include_mock=False)
    for record in records:
        if record.provider == "mock":
            continue
        prices = _extract_prices(record.payload.get("prices") or [])
        if prices:
            return record, prices
    return None, []


def build_current_portfolio_backtest_series(
    positions: list[dict],
    histories: dict[str, list[dict]],
    start_date: date,
    end_date: date,
    *,
    baseline_value: float | None = None,
    baseline_by_asset: dict[str, float] | None = None,
    monthly_contribution: float = 0,
) -> list[dict]:
    checkpoints = _month_checkpoints(start_date, end_date)
    if not checkpoints:
        return []
    position_baselines = _position_baselines(positions, histories, start_date, baseline_value, baseline_by_asset)
    asset_values = dict(position_baselines)
    start_values = _class_values_from_asset_values(positions, asset_values)
    previous = start_values
    previous_checkpoint = start_date
    total_contributed = 0.0
    compounded_return_factor = 1.0
    monthly_contribution = max(_float(monthly_contribution), 0.0)
    rows: list[dict] = []

    for index, checkpoint in enumerate(checkpoints):
        contribution_by_asset = {}
        contribution = 0.0
        if index > 0 and monthly_contribution > 0:
            contribution = monthly_contribution
            contribution_by_asset = _allocate_contribution(asset_values, positions, contribution)
            for asset_id, amount in contribution_by_asset.items():
                asset_values[asset_id] = _float(asset_values.get(asset_id)) + amount
            total_contributed += contribution

        if index > 0:
            _apply_asset_returns(asset_values, positions, histories, previous_checkpoint, checkpoint)

        values = _class_values_from_asset_values(positions, asset_values)
        total = values["totalValue"]
        risk_assets_value = values["stocksValue"] + values["cryptoValue"]
        contribution_values = _class_values_from_asset_values(positions, contribution_by_asset)
        performance_base_total = previous["totalValue"] + contribution
        performance_base_stocks = previous["stocksValue"] + contribution_values["stocksValue"]
        performance_base_crypto = previous["cryptoValue"] + contribution_values["cryptoValue"]
        performance_base_fixed_income = previous["fixedIncomeValue"] + contribution_values["fixedIncomeValue"]
        performance_base_risk_assets = (
            previous["stocksValue"]
            + previous["cryptoValue"]
            + contribution_values["stocksValue"]
            + contribution_values["cryptoValue"]
        )
        start_total = start_values["totalValue"]
        capital_base = start_total + total_contributed
        period_start = previous_checkpoint
        monthly_returns = _class_returns_between(positions, histories, period_start, checkpoint, asset_values)
        monthly_return_pct = monthly_returns["totalReturnPct"]
        risk_assets_return_pct = monthly_returns["riskAssetsReturnPct"]
        if index > 0:
            compounded_return_factor *= 1 + monthly_return_pct / 100
        cumulative_return_pct = round((compounded_return_factor - 1) * 100, 2)
        applied_capital_return_pct = _return_pct(total, capital_base)
        rows.append(
            {
                "month": f"{checkpoint.year}-{checkpoint.month:02d}",
                "periodLabel": "Inicio" if index == 0 else f"{checkpoint.year}-{checkpoint.month:02d}",
                "date": checkpoint.isoformat(),
                "stocksValue": round(values["stocksValue"], 2),
                "cryptoValue": round(values["cryptoValue"], 2),
                "fixedIncomeValue": round(values["fixedIncomeValue"], 2),
                "riskAssetsValue": round(risk_assets_value, 2),
                "totalValue": round(total, 2),
                "baselineValue": round(start_total, 2),
                "monthlyContribution": round(contribution, 2),
                "totalContributed": round(total_contributed, 2),
                "capitalBaseValue": round(capital_base, 2),
                "performancePnl": round(total - capital_base, 2),
                "performanceBaseTotal": round(performance_base_total, 2),
                "performanceBaseRiskAssets": round(performance_base_risk_assets, 2),
                "performanceBaseStocks": round(performance_base_stocks, 2),
                "performanceBaseCrypto": round(performance_base_crypto, 2),
                "performanceBaseFixedIncome": round(performance_base_fixed_income, 2),
                "monthlyReturnPct": monthly_return_pct,
                "riskAssetsReturnPct": risk_assets_return_pct,
                "stocksReturnPct": monthly_returns["stocksReturnPct"],
                "cryptoReturnPct": monthly_returns["cryptoReturnPct"],
                "fixedIncomeReturnPct": monthly_returns["fixedIncomeReturnPct"],
                "cumulativeReturnPct": cumulative_return_pct,
                "appliedCapitalReturnPct": applied_capital_return_pct,
            }
        )
        previous = values
        previous_checkpoint = checkpoint

    return rows


def _position_baselines(
    positions: list[dict],
    histories: dict[str, list[dict]],
    start_date: date,
    baseline_value: float | None,
    baseline_by_asset: dict[str, float] | None,
) -> dict[str, float]:
    baselines: dict[str, float] = {}
    if baseline_by_asset:
        for position in positions:
            baselines[position["assetId"]] = _float(baseline_by_asset.get(position["assetId"]))
        return baselines

    for position in positions:
        quantity = _float(position.get("quantity"))
        current_price = _float(position.get("currentPrice"))
        prices = histories.get(position["assetId"]) or []
        start_price = _price_at_or_before(prices, start_date, current_price)
        baselines[position["assetId"]] = quantity * start_price

    target_baseline = _float(baseline_value) if baseline_value is not None else 0.0
    raw_total = sum(baselines.values())
    if target_baseline and raw_total:
        scale = target_baseline / raw_total
        baselines = {asset_id: value * scale for asset_id, value in baselines.items()}
    return baselines


def _allocate_contribution(asset_values: dict[str, float], positions: list[dict], contribution: float) -> dict[str, float]:
    total = sum(max(_float(asset_values.get(position["assetId"])), 0.0) for position in positions)
    if total <= 0:
        return {}
    return {
        position["assetId"]: contribution * max(_float(asset_values.get(position["assetId"])), 0.0) / total
        for position in positions
    }


def _apply_asset_returns(
    asset_values: dict[str, float],
    positions: list[dict],
    histories: dict[str, list[dict]],
    previous_date: date,
    target: date,
) -> None:
    for position in positions:
        asset_id = position["assetId"]
        current_price = _float(position.get("currentPrice"))
        prices = histories.get(asset_id) or []
        previous_price = _price_at_or_before(prices, previous_date, current_price)
        price = _price_at_or_before(prices, target, current_price)
        ratio = price / previous_price if previous_price else 1.0
        asset_values[asset_id] = _float(asset_values.get(asset_id)) * ratio


def _class_returns_between(
    positions: list[dict],
    histories: dict[str, list[dict]],
    period_start: date,
    target: date,
    asset_values_at_target: dict[str, float],
) -> dict[str, float]:
    start_values = {"stocksValue": 0.0, "cryptoValue": 0.0, "fixedIncomeValue": 0.0, "totalValue": 0.0}
    end_values = {"stocksValue": 0.0, "cryptoValue": 0.0, "fixedIncomeValue": 0.0, "totalValue": 0.0}

    for position in positions:
        asset_id = position["assetId"]
        current_price = _float(position.get("currentPrice"))
        prices = histories.get(asset_id) or []
        start_price = _price_at_or_after(prices, period_start, current_price)
        end_price = current_price if target >= date.today() else _price_at_or_before(prices, target, current_price)
        quantity = _float(position.get("quantity"))
        start_value = quantity * start_price
        end_value = quantity * end_price

        if _is_crypto(position):
            bucket = "cryptoValue"
        elif _is_fixed_income(position):
            bucket = "fixedIncomeValue"
        else:
            bucket = "stocksValue"

        start_values[bucket] += start_value
        end_values[bucket] += end_value
        start_values["totalValue"] += start_value
        end_values["totalValue"] += end_value

    start_risk = start_values["stocksValue"] + start_values["cryptoValue"]
    end_risk = end_values["stocksValue"] + end_values["cryptoValue"]
    return {
        "monthlyReturnPct": _return_pct(end_values["totalValue"], start_values["totalValue"]),
        "totalReturnPct": _return_pct(end_values["totalValue"], start_values["totalValue"]),
        "riskAssetsReturnPct": _return_pct(end_risk, start_risk),
        "stocksReturnPct": _return_pct(end_values["stocksValue"], start_values["stocksValue"]),
        "cryptoReturnPct": _return_pct(end_values["cryptoValue"], start_values["cryptoValue"]),
        "fixedIncomeReturnPct": _return_pct(end_values["fixedIncomeValue"], start_values["fixedIncomeValue"]),
    }


def _class_values_from_asset_values(positions: list[dict], asset_values: dict[str, float]) -> dict:
    stocks = 0.0
    crypto = 0.0
    fixed_income = 0.0
    for position in positions:
        value = _float(asset_values.get(position["assetId"]))
        if _is_crypto(position):
            crypto += value
        elif _is_fixed_income(position):
            fixed_income += value
        else:
            stocks += value
    return {
        "stocksValue": stocks,
        "cryptoValue": crypto,
        "fixedIncomeValue": fixed_income,
        "totalValue": stocks + crypto + fixed_income,
    }


def _price_at_or_before(prices: list[dict], target: date, fallback: float) -> float:
    selected = None
    for row in prices:
        day = row["date"]
        if day <= target:
            selected = row
        else:
            break
    if selected is None and prices:
        selected = prices[0]
    return _float(selected.get("close") if selected else fallback)


def _price_at_or_after(prices: list[dict], target: date, fallback: float) -> float:
    for row in prices:
        if row["date"] >= target:
            return _float(row.get("close"))
    return _price_at_or_before(prices, target, fallback)


def _period_start_for_checkpoint(start_date: date, checkpoint: date, index: int) -> date:
    if index == 0:
        return checkpoint
    month_start = date(checkpoint.year, checkpoint.month, 1)
    if start_date.year == checkpoint.year and start_date.month == checkpoint.month:
        return start_date
    return month_start


def _extract_prices(rows: list[dict]) -> list[dict]:
    prices = []
    for row in rows:
        try:
            day = date.fromisoformat(str(row.get("date"))[:10])
        except Exception:
            continue
        close = _float(row.get("close"))
        if close <= 0:
            continue
        prices.append({"date": day, "close": close})
    return sorted(prices, key=lambda item: item["date"])


def _month_checkpoints(start_date: date, end_date: date) -> list[date]:
    checkpoints = [start_date]
    cursor = date(start_date.year, start_date.month, 1)
    while cursor <= end_date:
        month_end = _last_day_of_month(cursor)
        checkpoint = min(month_end, end_date)
        if checkpoint > checkpoints[-1]:
            checkpoints.append(checkpoint)
        cursor = _add_month(cursor)
    return checkpoints


def _last_day_of_month(day: date) -> date:
    return _add_month(date(day.year, day.month, 1)) - timedelta(days=1)


def _add_month(day: date) -> date:
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _normalize_range(start_date: date, end_date: date) -> tuple[date, date]:
    today = date.today()
    start = min(start_date, end_date)
    end = max(start_date, end_date)
    if end > today:
        end = today
    if start < date(2000, 1, 1):
        start = date(2000, 1, 1)
    if start == end:
        end = min(today, start + timedelta(days=31))
    return start, end


def _summary(
    rows: list[dict],
    positions: list[dict],
    sources: dict[str, str],
    warnings: list[str],
    monthly_contribution: float,
) -> dict:
    last = rows[-1] if rows else {}
    performance_rows = rows[1:] if len(rows) > 1 else rows
    monthly_returns = [row["monthlyReturnPct"] for row in performance_rows if row.get("monthlyReturnPct") is not None]
    risk_monthly_returns = [row["riskAssetsReturnPct"] for row in performance_rows if row.get("riskAssetsReturnPct") is not None]
    stocks_monthly_returns = [row["stocksReturnPct"] for row in performance_rows if row.get("stocksReturnPct") is not None]
    crypto_monthly_returns = [row["cryptoReturnPct"] for row in performance_rows if row.get("cryptoReturnPct") is not None]
    fixed_income_monthly_returns = [row["fixedIncomeReturnPct"] for row in performance_rows if row.get("fixedIncomeReturnPct") is not None]
    best = max(performance_rows, key=lambda row: row["monthlyReturnPct"], default={})
    worst = min(performance_rows, key=lambda row: row["monthlyReturnPct"], default={})
    source_counts = defaultdict(int)
    for provider in sources.values():
        source_counts[provider] += 1
    initial = rows[0] if rows else {}
    period_years, period_months = _period_lengths(rows)
    total_return = round(_float(last.get("cumulativeReturnPct")), 2)
    risk_return = _compound_return(risk_monthly_returns)
    stocks_return = _compound_return(stocks_monthly_returns)
    crypto_return = _compound_return(crypto_monthly_returns)
    fixed_income_return = _compound_return(fixed_income_monthly_returns)

    return {
        "assetCount": len(positions),
        "stockCount": sum(1 for position in positions if not _is_crypto(position) and not _is_fixed_income(position)),
        "cryptoCount": sum(1 for position in positions if _is_crypto(position)),
        "fixedIncomeCount": sum(1 for position in positions if _is_fixed_income(position)),
        "periodYears": round(period_years, 2),
        "periodMonths": round(period_months, 1),
        "initialValue": round(_float(rows[0].get("baselineValue") if rows else 0), 2),
        "finalValue": round(_float(last.get("totalValue")), 2),
        "initialStocksValue": round(_float(initial.get("stocksValue")), 2),
        "finalStocksValue": round(_float(last.get("stocksValue")), 2),
        "initialCryptoValue": round(_float(initial.get("cryptoValue")), 2),
        "finalCryptoValue": round(_float(last.get("cryptoValue")), 2),
        "initialFixedIncomeValue": round(_float(initial.get("fixedIncomeValue")), 2),
        "finalFixedIncomeValue": round(_float(last.get("fixedIncomeValue")), 2),
        "initialRiskAssetsValue": round(_float(initial.get("riskAssetsValue")), 2),
        "finalRiskAssetsValue": round(_float(last.get("riskAssetsValue")), 2),
        "monthlyContribution": round(_float(monthly_contribution), 2),
        "totalContributed": round(_float(last.get("totalContributed")), 2),
        "capitalBaseValue": round(_float(last.get("capitalBaseValue")), 2),
        "performancePnl": round(_float(last.get("performancePnl")), 2),
        "appliedCapitalReturnPct": round(_float(last.get("appliedCapitalReturnPct")), 2),
        "totalReturnPct": total_return,
        "riskAssetsReturnPct": risk_return,
        "stocksReturnPct": stocks_return,
        "cryptoReturnPct": crypto_return,
        "fixedIncomeReturnPct": fixed_income_return,
        "annualizedTotalReturnPct": _equivalent_return(total_return, period_years),
        "annualizedRiskAssetsReturnPct": _equivalent_return(risk_return, period_years),
        "annualizedStocksReturnPct": _equivalent_return(stocks_return, period_years),
        "annualizedCryptoReturnPct": _equivalent_return(crypto_return, period_years),
        "annualizedFixedIncomeReturnPct": _equivalent_return(fixed_income_return, period_years),
        "monthlyEquivalentTotalReturnPct": _equivalent_return(total_return, period_months),
        "monthlyEquivalentRiskAssetsReturnPct": _equivalent_return(risk_return, period_months),
        "monthlyEquivalentStocksReturnPct": _equivalent_return(stocks_return, period_months),
        "monthlyEquivalentCryptoReturnPct": _equivalent_return(crypto_return, period_months),
        "monthlyEquivalentFixedIncomeReturnPct": _equivalent_return(fixed_income_return, period_months),
        "averageMonthlyReturnPct": round(sum(monthly_returns) / len(monthly_returns), 2) if monthly_returns else 0,
        "averageRiskAssetsMonthlyReturnPct": round(sum(risk_monthly_returns) / len(risk_monthly_returns), 2) if risk_monthly_returns else 0,
        "averageStocksMonthlyReturnPct": round(sum(stocks_monthly_returns) / len(stocks_monthly_returns), 2) if stocks_monthly_returns else 0,
        "averageCryptoMonthlyReturnPct": round(sum(crypto_monthly_returns) / len(crypto_monthly_returns), 2) if crypto_monthly_returns else 0,
        "averageFixedIncomeMonthlyReturnPct": round(sum(fixed_income_monthly_returns) / len(fixed_income_monthly_returns), 2) if fixed_income_monthly_returns else 0,
        "bestMonth": {"month": best.get("month", ""), "returnPct": best.get("monthlyReturnPct", 0)},
        "worstMonth": {"month": worst.get("month", ""), "returnPct": worst.get("monthlyReturnPct", 0)},
        "realDataAssets": sum(count for provider, count in source_counts.items() if not provider.startswith("fallback")),
        "fallbackAssets": sum(count for provider, count in source_counts.items() if provider.startswith("fallback")),
        "sourceCounts": dict(source_counts),
        "warningCount": len(warnings),
    }


def _merge_total_return_summary(summary: dict, total_return_report: dict) -> None:
    returns = total_return_report.get("returns") or {}
    summary["incomeTotal"] = round(_float(total_return_report.get("incomeTotal")), 2)
    summary["incomeBreakdown"] = total_return_report.get("breakdown") or {}
    summary["totalReturnWithIncomePct"] = round(_float(returns.get("totalReturnWithIncomePct")), 2)
    summary["riskAssetsReturnWithIncomePct"] = round(_float(returns.get("riskAssetsReturnWithIncomePct")), 2)
    summary["stocksReturnWithIncomePct"] = round(_float(returns.get("stocksReturnWithIncomePct")), 2)
    summary["cryptoReturnWithIncomePct"] = round(_float(returns.get("cryptoReturnWithIncomePct")), 2)
    summary["fixedIncomeReturnWithIncomePct"] = round(_float(returns.get("fixedIncomeReturnWithIncomePct")), 2)
    summary["averageMonthlyTotalReturnWithIncomePct"] = round(_float(returns.get("averageMonthlyTotalReturnWithIncomePct")), 2)
    summary["averageMonthlyStocksReturnWithIncomePct"] = round(_float(returns.get("averageMonthlyStocksReturnWithIncomePct")), 2)


def _compound_return(monthly_returns: list[float]) -> float:
    factor = 1.0
    for value in monthly_returns:
        factor *= 1 + _float(value) / 100
    return round((factor - 1) * 100, 2)


def _equivalent_return(total_return_pct: float, periods: float) -> float:
    if periods <= 0 or total_return_pct <= -100:
        return 0.0
    return round(((1 + _float(total_return_pct) / 100) ** (1 / periods) - 1) * 100, 2)


def _period_lengths(rows: list[dict]) -> tuple[float, float]:
    if len(rows) < 2:
        return 0.0, 0.0
    try:
        start = date.fromisoformat(str(rows[0].get("date"))[:10])
        end = date.fromisoformat(str(rows[-1].get("date"))[:10])
    except Exception:
        return 0.0, 0.0
    days = max((end - start).days, 1)
    return days / 365.25, days / 30.4375


def _return_pct(value: float, base: float) -> float:
    if not base:
        return 0.0
    return round((value / base - 1) * 100, 2)


def _is_crypto(position: dict) -> bool:
    return str(position.get("class") or "").lower() in {"cripto", "crypto"}


def _is_fixed_income(position: dict) -> bool:
    return is_fixed_income_class(position.get("class")) or "cdi" in str(position.get("sector") or position.get("segment") or "").lower()


def _float(value) -> float:
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0.0
    except Exception:
        return 0.0
