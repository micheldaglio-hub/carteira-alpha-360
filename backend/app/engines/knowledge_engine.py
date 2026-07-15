from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AssetFact, AssetMetricDivergence, MarketDataProviderEvent
from app.services.market_data.v2.contracts import DATA_TYPE_FUNDAMENTALS, DATA_TYPE_QUOTE, NormalizedMarketData


OFFICIAL_OR_PRIMARY_SOURCES = {"brapi", "cvm", "b3"}
COMPARISON_SOURCE_FUNDAMENTUS = "fundamentus"

PERCENT_METRICS = {
    "dividend_yield",
    "payout",
    "revenue_growth",
    "profit_growth",
    "net_margin",
    "roe",
    "roic",
}
MONEY_METRICS = {"price", "revenue", "profit", "market_value"}
TRACKED_METRICS = {
    "price",
    "dividend_yield",
    "payout",
    "pe_ratio",
    "pvp",
    "ev_ebitda",
    "revenue_growth",
    "profit_growth",
    "net_margin",
    "roe",
    "roic",
    "debt_to_ebitda",
    "revenue",
    "profit",
    "market_value",
}


class KnowledgeEngine:
    """Stores treated market facts and flags source divergences.

    Screens and scores should consume treated facts/services instead of parsing raw
    provider responses directly. The engine never overwrites an official source
    with a secondary validation source.
    """

    divergence_threshold_pct = Decimal("15")

    def save_market_data(
        self,
        db: Session,
        asset_id: str | None,
        data: NormalizedMarketData,
        *,
        source: str | None = None,
    ) -> list[AssetFact]:
        if not asset_id or data.data_type not in {DATA_TYPE_FUNDAMENTALS, DATA_TYPE_QUOTE}:
            return []

        source_name = (source or data.provider or "").lower().strip()
        if not source_name:
            return []

        raw_payload_json = json.dumps(data.payload, ensure_ascii=False, sort_keys=True)
        saved: list[AssetFact] = []
        for metric_key, raw_value in data.payload.items():
            if metric_key not in TRACKED_METRICS:
                continue
            fact = self._upsert_fact(
                db,
                asset_id=asset_id,
                source=source_name,
                metric_key=metric_key,
                raw_value=raw_value,
                currency=data.currency,
                confidence=data.quality_score,
                raw_payload_json=raw_payload_json,
                as_of=data.as_of,
            )
            saved.append(fact)

        if source_name == COMPARISON_SOURCE_FUNDAMENTUS:
            self.compare_against_primary_sources(db, asset_id, saved)
        return saved

    def compare_against_primary_sources(self, db: Session, asset_id: str, comparison_facts: list[AssetFact]) -> list[AssetMetricDivergence]:
        divergences: list[AssetMetricDivergence] = []
        for comparison in comparison_facts:
            if comparison.value_numeric is None:
                continue
            primary = (
                db.execute(
                    select(AssetFact)
                    .where(
                        AssetFact.asset_id == asset_id,
                        AssetFact.metric_key == comparison.metric_key,
                        AssetFact.period == comparison.period,
                        AssetFact.source.in_(OFFICIAL_OR_PRIMARY_SOURCES),
                    )
                    .order_by(AssetFact.updated_at.desc())
                )
                .scalars()
                .first()
            )
            if primary is None or primary.value_numeric is None:
                continue

            divergence_pct = self._divergence_pct(primary.value_numeric, comparison.value_numeric)
            if divergence_pct < self.divergence_threshold_pct:
                continue

            divergence = self._upsert_divergence(
                db,
                asset_id=asset_id,
                metric_key=comparison.metric_key,
                primary_source=primary.source,
                comparison_source=comparison.source,
                primary_value=primary.value_numeric,
                comparison_value=comparison.value_numeric,
                divergence_pct=divergence_pct,
            )
            divergences.append(divergence)
        return divergences

    def record_provider_event(
        self,
        db: Session,
        *,
        provider: str,
        event_type: str,
        message: str,
        severity: str = "warning",
        status_code: str = "",
    ) -> MarketDataProviderEvent:
        event = MarketDataProviderEvent(
            provider=provider,
            event_type=event_type,
            severity=severity,
            message=message[:2000],
            status_code=status_code,
        )
        db.add(event)
        db.flush()
        return event

    def _upsert_fact(
        self,
        db: Session,
        *,
        asset_id: str,
        source: str,
        metric_key: str,
        raw_value: Any,
        currency: str,
        confidence: float,
        raw_payload_json: str,
        as_of: datetime,
        period: str = "latest",
    ) -> AssetFact:
        numeric = self._to_decimal(raw_value)
        value_text = "" if raw_value is None else str(raw_value)
        fact = (
            db.execute(
                select(AssetFact).where(
                    AssetFact.asset_id == asset_id,
                    AssetFact.source == source,
                    AssetFact.metric_key == metric_key,
                    AssetFact.period == period,
                )
            )
            .scalars()
            .first()
        )
        if fact is None:
            fact = AssetFact(asset_id=asset_id, source=source, metric_key=metric_key, period=period)
            db.add(fact)

        fact.value_numeric = numeric
        fact.value_text = value_text
        fact.currency = currency if metric_key in MONEY_METRICS else ""
        fact.unit = self._unit_for(metric_key)
        fact.confidence = Decimal(str(round(float(confidence or 0), 2)))
        fact.raw_payload_json = raw_payload_json
        fact.as_of = as_of
        fact.updated_at = datetime.now(timezone.utc)
        db.flush()
        return fact

    def _upsert_divergence(
        self,
        db: Session,
        *,
        asset_id: str,
        metric_key: str,
        primary_source: str,
        comparison_source: str,
        primary_value: Decimal,
        comparison_value: Decimal,
        divergence_pct: Decimal,
    ) -> AssetMetricDivergence:
        divergence = (
            db.execute(
                select(AssetMetricDivergence).where(
                    AssetMetricDivergence.asset_id == asset_id,
                    AssetMetricDivergence.metric_key == metric_key,
                    AssetMetricDivergence.primary_source == primary_source,
                    AssetMetricDivergence.comparison_source == comparison_source,
                    AssetMetricDivergence.status == "open",
                )
            )
            .scalars()
            .first()
        )
        if divergence is None:
            divergence = AssetMetricDivergence(
                asset_id=asset_id,
                metric_key=metric_key,
                primary_source=primary_source,
                comparison_source=comparison_source,
            )
            db.add(divergence)

        divergence.primary_value = primary_value
        divergence.comparison_value = comparison_value
        divergence.divergence_pct = divergence_pct
        db.flush()
        return divergence

    def _to_decimal(self, value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _divergence_pct(self, primary_value: Decimal, comparison_value: Decimal) -> Decimal:
        if primary_value == 0:
            return Decimal("100") if comparison_value != 0 else Decimal("0")
        return abs((comparison_value - primary_value) / primary_value * Decimal("100")).quantize(Decimal("0.0001"))

    def _unit_for(self, metric_key: str) -> str:
        if metric_key in PERCENT_METRICS:
            return "percent"
        if metric_key in MONEY_METRICS:
            return "money"
        return "multiple"
