from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.services.data_lineage import data_lineage_summary, record_evidence_batch


def record_dashboard_evidence(db: Session, user_id: str, dashboard: dict) -> dict:
    metrics = dashboard.get("metrics") or {}
    snapshot = dashboard.get("portfolioSnapshot") or {}
    rows: list[dict[str, Any]] = []
    base_payload = {
        "metricKeys": sorted(metrics.keys()),
        "classCount": len(((snapshot.get("allocations") or {}).get("byClass") or [])),
        "positionCount": len(snapshot.get("positions") or []),
    }
    for field_name, formula_name, confidence in [
        ("totalEquity", "portfolio_current_value_plus_external_accounts", 91),
        ("investedValue", "average_cost_adjusted_by_transactions", 90),
        ("pnl", "total_equity_minus_invested_value", 90),
        ("pnlPct", "pnl_divided_by_invested_value", 90),
        ("projectedPassiveIncome", "projected_proceeds_income_plus_projected_fixed_income", 86),
        ("projectedProceedsIncome", "current_yield_based_proceeds_projection", 82),
        ("projectedFixedIncome", "cdi_daily_rate_compounded_to_month", 88),
        ("proceedsYear", "sum_recorded_proceeds_year", 88),
        ("projection10y", "dashboard_projection_10_years_from_saved_premises", 78),
        ("projection20y", "dashboard_projection_20_years_from_saved_premises", 78),
        ("projection30y", "dashboard_projection_30_years_from_saved_premises", 78),
    ]:
        rows.append(
            _row(
                user_id,
                domain="dashboard",
                field_name=field_name,
                value_numeric=metrics.get(field_name),
                currency="BRL" if field_name != "pnlPct" else "",
                unit="pct" if field_name == "pnlPct" else "",
                provider="portfolio_service",
                source_type="formula",
                source_ref=f"dashboard.metrics.{field_name}",
                formula_name=formula_name,
                input_payload=base_payload,
                confidence=confidence,
                quality_score=confidence,
            )
        )

    for position in snapshot.get("positions") or []:
        fixed_income = position.get("fixedIncome") or {}
        if not fixed_income:
            continue
        provider = str(fixed_income.get("source") or "fixed_income_engine")
        is_provider = "Banco Central" in provider
        confidence = 88 if is_provider else 45
        source_type = "provider" if is_provider else "fallback"
        for field_name, value, unit, formula in [
            ("currentValue", position.get("currentValue"), "BRL", "fixed_income_lot_accrual"),
            ("pnl", position.get("pnl"), "BRL", "fixed_income_current_minus_invested"),
            ("returnPct", position.get("returnPct"), "pct", "fixed_income_return_pct"),
            ("dailyRatePct", fixed_income.get("dailyRatePct"), "pct", "cdi_daily_rate"),
            ("appliedDays", fixed_income.get("appliedDays"), "days", "business_days_with_cdi_rates"),
        ]:
            rows.append(
                _row(
                    user_id,
                    domain="fixed_income",
                    field_name=field_name,
                    asset_id=position.get("assetId"),
                    value_numeric=value,
                    currency="BRL" if unit == "BRL" else "",
                    unit=unit if unit != "BRL" else "",
                    provider=provider,
                    source_type=source_type,
                    source_ref=f"portfolioSnapshot.positions.{position.get('ticker')}.{field_name}",
                    formula_name=formula,
                    input_payload=fixed_income,
                    confidence=confidence,
                    quality_score=confidence,
                    status="ok" if is_provider else "fallback",
                    metadata={"ticker": position.get("ticker"), "class": position.get("class")},
                )
            )
    return _persist(db, user_id, rows)


def record_projection_evidence(db: Session, user_id: str, payload: Any, result: dict, current_wealth_for_goal: float | None) -> dict:
    payload_dict = _as_plain_dict(payload)
    summary = result.get("summary") or {}
    breakdown = result.get("breakdown") or {}
    independence = result.get("independence") or {}
    rows: list[dict[str, Any]] = []
    for field_name, value, source_ref in [
        ("finalValue", summary.get("finalValue"), "summary.finalValue"),
        ("totalContributed", summary.get("totalContributed"), "summary.totalContributed"),
        ("totalProceeds", summary.get("totalProceeds", summary.get("totalDividends")), "summary.totalProceeds"),
        ("estimatedYearsToGoal", summary.get("estimatedYearsToGoal"), "summary.estimatedYearsToGoal"),
        ("capitalGain", breakdown.get("capitalGain", summary.get("totalInterest")), "breakdown.capitalGain"),
        ("totalReturn", breakdown.get("totalReturn"), "breakdown.totalReturn"),
        ("finalReal", breakdown.get("finalReal"), "breakdown.finalReal"),
        ("monthlyPassiveIncome", independence.get("monthlyPassiveIncome"), "independence.monthlyPassiveIncome"),
        ("requiredWealth", independence.get("requiredWealth"), "independence.requiredWealth"),
        ("remainingWealth", independence.get("remainingWealth"), "independence.remainingWealth"),
        ("currentWealthForGoal", current_wealth_for_goal or independence.get("currentWealthForGoal"), "independence.currentWealthForGoal"),
    ]:
        rows.append(
            _row(
                user_id,
                domain="financial_projection",
                field_name=field_name,
                value_numeric=value,
                currency="BRL" if field_name not in {"estimatedYearsToGoal"} else "",
                unit="years" if field_name == "estimatedYearsToGoal" else "",
                provider="financial_projection_engine",
                source_type="formula",
                source_ref=source_ref,
                formula_name=f"financial_projection_engine.{field_name}",
                input_payload=payload_dict,
                confidence=90,
                quality_score=90,
                metadata={"currentWealthForGoal": current_wealth_for_goal},
            )
        )
    return _persist(db, user_id, rows)


def record_tax_evidence(db: Session, user_id: str, report: dict) -> dict:
    rows = []
    for field_name in ["grossIncome", "realizedGain", "estimatedWithheldTax", "estimatedTaxDue", "netIncomeAfterEstimatedTax"]:
        rows.append(
            _row(
                user_id,
                domain="tax",
                field_name=field_name,
                value_numeric=report.get(field_name),
                currency="BRL",
                provider="tax_engine",
                source_type="formula",
                source_ref=f"tax.{field_name}",
                formula_name=f"tax_engine.{field_name}",
                input_payload={"period": report.get("period"), "items": len(report.get("items") or []), "rules": [item.get("id") for item in report.get("rules") or []]},
                confidence=76,
                quality_score=76,
                metadata={"jurisdiction": report.get("jurisdiction"), "status": report.get("status")},
            )
        )
    return _persist(db, user_id, rows)


def record_stress_evidence(db: Session, user_id: str, report: dict) -> dict:
    rows = []
    for field_name, unit in [
        ("baseEquity", "BRL"),
        ("basePassiveIncome", "BRL"),
        ("worstImpactValue", "BRL"),
        ("worstImpactPct", "pct"),
        ("resilienceScore", "score"),
    ]:
        rows.append(
            _row(
                user_id,
                domain="stress_test",
                field_name=field_name,
                value_numeric=report.get(field_name),
                currency="BRL" if unit == "BRL" else "",
                unit="" if unit == "BRL" else unit,
                provider="scenario_engine",
                source_type="formula",
                source_ref=f"stressTest.{field_name}",
                formula_name=f"scenario_engine.{field_name}",
                input_payload={"worstScenarioId": report.get("worstScenarioId"), "scenarioCount": len(report.get("scenarios") or [])},
                confidence=82,
                quality_score=82,
                metadata={"riskLevel": report.get("riskLevel")},
            )
        )
    return _persist(db, user_id, rows)


def record_strategy_evidence(db: Session, user_id: str, report: dict) -> dict:
    metrics = report.get("metrics") or {}
    rows = [
        _row(
            user_id,
            domain="strategy",
            field_name="primaryScore",
            value_numeric=report.get("primaryScore"),
            unit="score",
            provider="strategy_engine",
            source_type="formula",
            source_ref="strategy.primaryScore",
            formula_name="strategy_engine.weighted_fit_score",
            input_payload={"primaryStrategy": report.get("primaryStrategy"), "metrics": metrics},
            confidence=84,
            quality_score=84,
            metadata={"primaryStrategy": report.get("primaryStrategy")},
        )
    ]
    for field_name in ["globalExposure", "cryptoWeight", "largestAssetWeight", "incomeYield"]:
        rows.append(
            _row(
                user_id,
                domain="strategy",
                field_name=field_name,
                value_numeric=metrics.get(field_name),
                unit="pct",
                provider="strategy_engine",
                source_type="formula",
                source_ref=f"strategy.metrics.{field_name}",
                formula_name=f"strategy_engine.{field_name}",
                input_payload=metrics,
                confidence=82,
                quality_score=82,
            )
        )
    return _persist(db, user_id, rows)


def record_recommended_portfolio_evidence(db: Session, user_id: str, report: dict) -> dict:
    breakdown = report.get("scoreBreakdown") or {}
    rows = [
        _row(
            user_id,
            domain="recommendation",
            field_name="institutionalScore",
            value_numeric=report.get("institutionalScore"),
            unit="score",
            provider="recommended_portfolio_engine",
            source_type="formula",
            source_ref="recommendedPortfolioReport.institutionalScore",
            formula_name="recommended_portfolio_engine.institutional_score",
            input_payload={"scoreBreakdown": breakdown, "confidenceScore": report.get("confidenceScore"), "riskLevel": report.get("riskLevel")},
            confidence=86,
            quality_score=86,
            metadata={"reportMonth": report.get("reportMonth"), "classification": report.get("classification")},
        ),
        _row(
            user_id,
            domain="recommendation",
            field_name="confidenceScore",
            value_numeric=report.get("confidenceScore"),
            unit="score",
            provider="alpha_confidence_engine",
            source_type="formula",
            source_ref="recommendedPortfolioReport.confidenceScore",
            formula_name="alpha_confidence_engine.overall_score",
            input_payload={"reportMonth": report.get("reportMonth")},
            confidence=84,
            quality_score=84,
        ),
    ]
    for field_name, value in breakdown.items():
        rows.append(
            _row(
                user_id,
                domain="recommendation",
                field_name=f"scoreBreakdown.{field_name}",
                value_numeric=value,
                unit="score",
                provider="recommended_portfolio_engine",
                source_type="formula",
                source_ref=f"recommendedPortfolioReport.scoreBreakdown.{field_name}",
                formula_name=f"recommended_portfolio_engine.{field_name}",
                input_payload=breakdown,
                confidence=82,
                quality_score=82,
            )
        )
    return _persist(db, user_id, rows)


def record_copilot_evidence(db: Session, user_id: str, response: dict) -> dict:
    confidence = _confidence_to_number(response.get("confidence"))
    rows = [
        _row(
            user_id,
            domain="copilot",
            field_name="answer",
            value_text=str(response.get("answer") or "")[:1000],
            provider=str(response.get("provider") or response.get("mode") or "alpha_copilot"),
            source_type="formula",
            source_ref="copilot.answer",
            formula_name="alpha_copilot_grounded_response",
            input_payload={"question": response.get("question"), "dataUsed": response.get("dataUsed") or []},
            confidence=confidence,
            quality_score=confidence,
            metadata={"citations": len(response.get("citations") or []), "mode": response.get("mode")},
        ),
        _row(
            user_id,
            domain="copilot",
            field_name="citationCount",
            value_numeric=len(response.get("citations") or response.get("dataUsed") or []),
            unit="count",
            provider="alpha_copilot",
            source_type="system",
            source_ref="copilot.citations",
            formula_name="copilot_internal_source_counter",
            input_payload=response,
            confidence=confidence,
            quality_score=confidence,
        ),
    ]
    return _persist(db, user_id, rows)


def record_macro_fx_evidence(db: Session, user_id: str, snapshot: dict) -> dict:
    rows: list[dict[str, Any]] = []
    for item in snapshot.get("indicators") or []:
        rows.append(
            _row(
                user_id,
                domain="macro_fx",
                field_name=str(item.get("id") or item.get("title") or "indicator"),
                value_numeric=item.get("value"),
                unit=str(item.get("unit") or ""),
                provider=str(item.get("source") or "macro_fx_engine"),
                source_type="provider" if item.get("sourceCode") else "fallback",
                source_ref=str(item.get("sourceCode") or item.get("title") or ""),
                formula_name="macro_fx_engine.indicator_snapshot",
                input_payload={"period": item.get("period"), "asOf": item.get("asOf"), "trend": item.get("trend")},
                confidence=item.get("qualityScore") or 70,
                quality_score=item.get("qualityScore") or 70,
                status=str(item.get("status") or "ok"),
                metadata={"title": item.get("title"), "reading": item.get("reading")},
            )
        )
    for item in snapshot.get("fxRates") or []:
        rows.append(
            _row(
                user_id,
                domain="macro_fx",
                field_name=str(item.get("pair") or "fx_rate"),
                value_numeric=item.get("rate"),
                currency=str(item.get("quoteCurrency") or ""),
                unit="fx_rate",
                provider=str(item.get("source") or "fx_provider"),
                source_type="provider" if item.get("sourceCode") else "fallback",
                source_ref=str(item.get("sourceCode") or item.get("pair") or ""),
                formula_name="macro_fx_engine.fx_snapshot",
                input_payload={"baseCurrency": item.get("baseCurrency"), "quoteCurrency": item.get("quoteCurrency"), "asOf": item.get("asOf")},
                confidence=item.get("qualityScore") or 70,
                quality_score=item.get("qualityScore") or 70,
                status=str(item.get("status") or "ok"),
                metadata={"reading": item.get("reading")},
            )
        )
    return _persist(db, user_id, rows)


def _row(
    user_id: str,
    *,
    domain: str,
    field_name: str,
    value_numeric: Any = None,
    value_text: str = "",
    asset_id: str | None = None,
    currency: str = "",
    unit: str = "",
    provider: str = "",
    source_type: str = "formula",
    source_ref: str = "",
    formula_name: str = "",
    input_payload: dict[str, Any] | None = None,
    confidence: float = 0,
    quality_score: float = 0,
    status: str = "ok",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "asset_id": asset_id,
        "domain": domain,
        "field_name": field_name,
        "value_numeric": _number_or_none(value_numeric),
        "value_text": value_text,
        "currency": currency,
        "unit": unit,
        "provider": provider,
        "source_type": source_type,
        "source_ref": source_ref,
        "formula_name": formula_name,
        "input_payload": input_payload or {},
        "confidence": confidence,
        "quality_score": quality_score,
        "status": status,
        "metadata": metadata or {},
    }


def _persist(db: Session, user_id: str, rows: list[dict[str, Any]]) -> dict:
    rows = [row for row in rows if row.get("value_numeric") is not None or row.get("value_text")]
    if not rows:
        return {"status": "no_evidence_recorded", "evidenceCount": 0}
    try:
        evidence = record_evidence_batch(db, rows)
        db.commit()
        summary = data_lineage_summary(db, user_id=user_id)
        return {"status": "recorded", "evidenceCount": len(evidence), "summary": summary}
    except Exception as exc:
        db.rollback()
        return {"status": "not_persisted", "evidenceCount": 0, "error": str(exc)[:180]}


def _as_plain_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    try:
        return dict(value)
    except Exception:
        return {"value": str(value)}


def _number_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _confidence_to_number(value: Any) -> float:
    raw = str(value or "").lower()
    if raw in {"alta", "high"}:
        return 88
    if raw in {"media", "medium"}:
        return 70
    if raw in {"baixa", "low"}:
        return 45
    return _number_or_none(value) or 62
