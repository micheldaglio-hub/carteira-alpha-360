from __future__ import annotations

import calendar
import json
from datetime import date, datetime
from decimal import Decimal
from math import isfinite
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    Asset,
    PublicationAsset,
    PublicationVersion,
    ResearchAttributionAsset,
    ResearchAttributionRun,
    ResearchPublication,
)
from app.services.data_lineage import record_data_evidence
from app.services.market_data.v2.contracts import DATA_TYPE_PRICE_HISTORY, MarketDataRequest, NormalizedMarketData
from app.services.market_data.v2.engine import MarketDataEngine


PERFORMANCE_ATTRIBUTION_VERSION = "2026.07.attrib1"


def run_performance_attribution_for_publication(
    db: Session,
    *,
    publication: ResearchPublication,
    publication_version: PublicationVersion | None = None,
    user_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    benchmark_name: str = "",
    benchmark_return_pct: float | None = None,
    refresh_market: bool = False,
    commit: bool = True,
) -> dict[str, Any]:
    version = publication_version or _latest_version(db, publication)
    if version is None:
        raise ValueError("Publicacao premium sem versao para atribuir performance.")

    period_start, period_end = _resolve_period(publication.period, start_date=start_date, end_date=end_date)
    asset_rows = list(
        db.execute(
            select(PublicationAsset)
            .where(
                PublicationAsset.publication_id == publication.id,
                PublicationAsset.version_id == version.id,
            )
            .order_by(desc(PublicationAsset.target_weight), PublicationAsset.ticker.asc())
        )
        .scalars()
        .all()
    )

    total_weight = sum(max(0.0, _number(row.target_weight)) for row in asset_rows)
    warnings: list[str] = []
    if not asset_rows:
        warnings.append("Nenhum ativo foi encontrado nesta versao da publicacao.")
    if total_weight <= 0 and asset_rows:
        warnings.append("Pesos-alvo ausentes; a atribuicao usou pesos iguais para todos os ativos.")
        total_weight = float(len(asset_rows))

    run = ResearchAttributionRun(
        publication_id=publication.id,
        publication_version_id=version.id,
        period=publication.period,
        start_date=period_start,
        end_date=period_end,
        status="completed" if asset_rows else "empty",
        benchmark_name=benchmark_name or "benchmark_nao_configurado",
        benchmark_return_pct=_decimal(benchmark_return_pct),
        source_engine="performance_attribution_engine",
        methodology_version=PERFORMANCE_ATTRIBUTION_VERSION,
        created_by_user_id=user_id,
        metadata_json=_json(
            {
                "publicationVersion": version.version,
                "refreshMarket": refresh_market,
                "benchmarkConfigured": benchmark_return_pct is not None or bool(benchmark_name),
            }
        ),
    )
    db.add(run)
    db.flush()

    attribution_rows: list[ResearchAttributionAsset] = []
    for item in asset_rows:
        normalized_weight = _normalized_weight(item, total_weight, len(asset_rows))
        result = _attribute_asset(
            db,
            item,
            period_start=period_start,
            period_end=period_end,
            normalized_weight=normalized_weight,
            user_id=user_id,
            refresh_market=refresh_market,
            publication_id=publication.id,
            version_id=version.id,
        )
        row = ResearchAttributionAsset(
            run_id=run.id,
            asset_id=item.asset_id,
            ticker=result["ticker"],
            asset_name=result["assetName"],
            asset_class=result["assetClass"],
            sector=result["sector"],
            target_weight=_decimal(item.target_weight),
            start_price=_decimal(result["startPrice"]),
            end_price=_decimal(result["endPrice"]),
            price_return_pct=_decimal(result["priceReturnPct"]),
            income_return_pct=_decimal(result["incomeReturnPct"]),
            total_return_pct=_decimal(result["totalReturnPct"]),
            contribution_pct=_decimal(result["contributionPct"]),
            data_quality_score=_decimal(result["dataQualityScore"]),
            provider=result["provider"],
            source_type=result["sourceType"],
            status=result["status"],
            evidence_ids_json=_json(result["evidenceIds"]),
            metadata_json=_json(result["metadata"]),
        )
        db.add(row)
        attribution_rows.append(row)
        warnings.extend(result["warnings"])

    db.flush()
    price_return_pct = sum(_number(row.price_return_pct) * _normalized_weight_by_row(row, total_weight, len(attribution_rows)) / 100 for row in attribution_rows)
    income_return_pct = sum(_number(row.income_return_pct) * _normalized_weight_by_row(row, total_weight, len(attribution_rows)) / 100 for row in attribution_rows)
    portfolio_return_pct = sum(_number(row.contribution_pct) for row in attribution_rows)
    benchmark_configured = benchmark_return_pct is not None or bool(benchmark_name)
    benchmark_value = _number(benchmark_return_pct) if benchmark_configured else 0.0
    excess_return_pct = portfolio_return_pct - benchmark_value if benchmark_configured else 0.0
    quality_score = _weighted_quality(attribution_rows, total_weight)

    top_contributors = _contributors(attribution_rows, reverse=True)
    detractors = _contributors(attribution_rows, reverse=False)
    if not benchmark_configured:
        warnings.append("Benchmark nao configurado; excesso de retorno foi mantido em 0 para evitar leitura enganosa.")

    run.portfolio_return_pct = _decimal(portfolio_return_pct)
    run.benchmark_return_pct = _decimal(benchmark_value)
    run.excess_return_pct = _decimal(excess_return_pct)
    run.price_return_pct = _decimal(price_return_pct)
    run.income_return_pct = _decimal(income_return_pct)
    run.data_quality_score = _decimal(quality_score)
    run.top_contributors_json = _json(top_contributors)
    run.detractors_json = _json(detractors)
    run.warnings_json = _json(_unique(warnings))
    run.summary = _summary(run, top_contributors, detractors, benchmark_configured)

    evidence = record_data_evidence(
        db,
        user_id=user_id,
        domain="premium_research_attribution",
        field_name="portfolio_return_pct",
        value_numeric=portfolio_return_pct,
        unit="pct",
        provider="performance_attribution_engine",
        source_type="formula",
        source_ref=f"researchPublication:{publication.id}:version:{version.id}:run:{run.id}",
        formula_name="portfolio_total_return_attribution",
        formula_version=PERFORMANCE_ATTRIBUTION_VERSION,
        input_payload={
            "publicationId": publication.id,
            "versionId": version.id,
            "period": publication.period,
            "startDate": period_start.isoformat() if period_start else "",
            "endDate": period_end.isoformat() if period_end else "",
            "assetCount": len(attribution_rows),
            "benchmarkName": run.benchmark_name,
            "benchmarkReturnPct": benchmark_value,
        },
        confidence=quality_score,
        quality_score=quality_score,
        status="ok" if quality_score >= 60 else "partial",
        metadata={"runId": run.id, "methodologyVersion": PERFORMANCE_ATTRIBUTION_VERSION},
    )
    run.metadata_json = _json(_json_load(run.metadata_json, {}) | {"portfolioEvidenceId": evidence.id})

    if commit:
        db.commit()
        db.refresh(run)
    return attribution_run_to_dict(run)


def attribution_run_to_dict(run: ResearchAttributionRun, *, include_assets: bool = True) -> dict[str, Any]:
    payload = {
        "id": run.id,
        "publicationId": run.publication_id,
        "publicationVersionId": run.publication_version_id,
        "period": run.period,
        "startDate": run.start_date.isoformat() if run.start_date else "",
        "endDate": run.end_date.isoformat() if run.end_date else "",
        "status": run.status,
        "benchmarkName": run.benchmark_name,
        "portfolioReturnPct": _round(_number(run.portfolio_return_pct), 4),
        "benchmarkReturnPct": _round(_number(run.benchmark_return_pct), 4),
        "excessReturnPct": _round(_number(run.excess_return_pct), 4),
        "priceReturnPct": _round(_number(run.price_return_pct), 4),
        "incomeReturnPct": _round(_number(run.income_return_pct), 4),
        "dataQualityScore": _round(_number(run.data_quality_score), 2),
        "sourceEngine": run.source_engine,
        "methodologyVersion": run.methodology_version,
        "summary": run.summary,
        "topContributors": _json_load(run.top_contributors_json, []),
        "detractors": _json_load(run.detractors_json, []),
        "warnings": _json_load(run.warnings_json, []),
        "metadata": _json_load(run.metadata_json, {}),
        "createdByUserId": run.created_by_user_id,
        "createdAt": run.created_at.isoformat() if run.created_at else "",
    }
    if include_assets:
        rows = sorted(run.asset_rows, key=lambda row: _number(row.contribution_pct), reverse=True)
        payload["assetRows"] = [_asset_row_to_dict(row) for row in rows]
    return payload


def _attribute_asset(
    db: Session,
    row: PublicationAsset,
    *,
    period_start: date,
    period_end: date,
    normalized_weight: float,
    user_id: str | None,
    refresh_market: bool,
    publication_id: str,
    version_id: str,
) -> dict[str, Any]:
    asset = row.asset or (db.get(Asset, row.asset_id) if row.asset_id else None)
    ticker = (row.ticker or (asset.ticker if asset else "")).upper()
    asset_class = asset.asset_class if asset else ""
    sector = asset.sector if asset else ""
    warnings: list[str] = []
    record, prices = _price_history(db, asset, ticker, period_start, period_end, refresh_market=refresh_market)
    snapshot_price = _snapshot_price(asset)
    start_price, end_price = _period_prices(prices, period_start, period_end, snapshot_price)
    provider = record.provider if record and prices else "asset_snapshot"
    source_type = "provider" if record and prices else "fallback"
    status = "ok" if record and prices and start_price > 0 and end_price > 0 else "fallback"
    quality_score = _number(record.quality_score) if record and prices else (45.0 if snapshot_price > 0 else 0.0)
    if source_type == "fallback":
        warnings.append(f"{ticker} sem historico suficiente no periodo; usado preco atual/snapshot.")

    price_return_pct = ((end_price / start_price) - 1) * 100 if start_price > 0 and end_price > 0 else 0.0
    income_return_pct = _income_return_pct(asset, period_start, period_end)
    total_return_pct = price_return_pct + income_return_pct
    contribution_pct = normalized_weight / 100 * total_return_pct
    evidence = record_data_evidence(
        db,
        user_id=user_id,
        asset_id=row.asset_id,
        domain="premium_research_attribution",
        field_name="asset_total_return_pct",
        value_numeric=total_return_pct,
        unit="pct",
        provider=provider,
        source_type=source_type,
        source_ref=f"researchPublication:{publication_id}:version:{version_id}:asset:{ticker}",
        formula_name="asset_total_return_attribution",
        formula_version=PERFORMANCE_ATTRIBUTION_VERSION,
        input_payload={
            "ticker": ticker,
            "targetWeight": _number(row.target_weight),
            "normalizedWeight": normalized_weight,
            "startDate": period_start.isoformat(),
            "endDate": period_end.isoformat(),
            "startPrice": start_price,
            "endPrice": end_price,
            "incomeReturnPct": income_return_pct,
            "priceSource": provider,
            "status": status,
        },
        confidence=quality_score,
        quality_score=quality_score,
        status="ok" if quality_score >= 60 else "partial",
        metadata={"publicationId": publication_id, "versionId": version_id, "ticker": ticker},
    )
    return {
        "ticker": ticker,
        "assetName": row.asset_name or (asset.name if asset else ticker),
        "assetClass": asset_class,
        "sector": sector,
        "startPrice": start_price,
        "endPrice": end_price,
        "priceReturnPct": price_return_pct,
        "incomeReturnPct": income_return_pct,
        "totalReturnPct": total_return_pct,
        "contributionPct": contribution_pct,
        "dataQualityScore": quality_score,
        "provider": provider,
        "sourceType": source_type,
        "status": status,
        "evidenceIds": [evidence.id],
        "warnings": warnings,
        "metadata": {
            "normalizedWeight": normalized_weight,
            "publicationAssetId": row.id,
            "recordProvider": record.provider if record else "",
            "recordWarnings": list(record.warnings) if record else [],
        },
    }


def _price_history(
    db: Session,
    asset: Asset | None,
    ticker: str,
    start_date: date,
    end_date: date,
    *,
    refresh_market: bool,
) -> tuple[NormalizedMarketData | None, list[dict[str, Any]]]:
    if not refresh_market or not ticker:
        return None, []
    try:
        engine = MarketDataEngine(db=db)
        request = MarketDataRequest(
            symbol=ticker,
            asset_id=asset.id if asset else None,
            provider_symbol=(asset.provider_symbol if asset else "") or ticker,
            market=(asset.market if asset else "") or ("Crypto" if (asset and asset.asset_class.lower() == "crypto") else "B3"),
            asset_class=asset.asset_class if asset else "",
            currency=(asset.currency if asset else "") or "BRL",
            start_date=start_date,
            end_date=end_date,
            interval="1day",
        )
        records = engine.collect(DATA_TYPE_PRICE_HISTORY, request, include_mock=False)
    except Exception:
        return None, []
    for record in records:
        prices = _extract_price_rows(record.payload.get("prices") or record.payload.get("historical") or [])
        if prices:
            return record, prices
    return None, []


def _extract_price_rows(rows: Any) -> list[dict[str, Any]]:
    prices = []
    for item in rows or []:
        day = _parse_price_date(item.get("date") if isinstance(item, dict) else None)
        close = item.get("close", item.get("price", item.get("adjClose"))) if isinstance(item, dict) else None
        if day is None or close is None:
            continue
        value = _number(close)
        if value > 0:
            prices.append({"date": day, "close": value})
    return sorted(prices, key=lambda item: item["date"])


def _period_prices(prices: list[dict[str, Any]], start_date: date, end_date: date, fallback: float) -> tuple[float, float]:
    start_price = fallback
    end_price = fallback
    for row in prices:
        if row["date"] >= start_date:
            start_price = row["close"]
            break
    for row in prices:
        if row["date"] <= start_date:
            start_price = row["close"]
    for row in prices:
        if row["date"] <= end_date:
            end_price = row["close"]
    return _round(start_price, 6), _round(end_price, 6)


def _income_return_pct(asset: Asset | None, start_date: date, end_date: date) -> float:
    if not asset or not asset.snapshot:
        return 0.0
    annual_yield = _number(asset.snapshot.dividend_yield)
    if annual_yield <= 0:
        return 0.0
    days = max(1, (end_date - start_date).days + 1)
    return annual_yield * days / 365


def _snapshot_price(asset: Asset | None) -> float:
    if not asset:
        return 0.0
    snapshot_price = _number(asset.snapshot.price if asset.snapshot else 0)
    return snapshot_price or _number(asset.last_price)


def _latest_version(db: Session, publication: ResearchPublication) -> PublicationVersion | None:
    return db.execute(
        select(PublicationVersion)
        .where(PublicationVersion.publication_id == publication.id)
        .order_by(desc(PublicationVersion.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _resolve_period(period: str, *, start_date: date | None, end_date: date | None) -> tuple[date, date]:
    if start_date and end_date:
        return start_date, end_date
    today = date.today()
    try:
        year, month = [int(part) for part in str(period or "").split("-")[:2]]
    except Exception:
        year, month = today.year, today.month
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return start_date or first, end_date or min(today, last)


def _normalized_weight(row: PublicationAsset, total_weight: float, asset_count: int) -> float:
    if total_weight <= 0 and asset_count:
        return 100 / asset_count
    return max(0.0, _number(row.target_weight)) / total_weight * 100 if total_weight > 0 else 0.0


def _normalized_weight_by_row(row: ResearchAttributionAsset, total_weight: float, asset_count: int) -> float:
    if total_weight <= 0 and asset_count:
        return 100 / asset_count
    return max(0.0, _number(row.target_weight)) / total_weight * 100 if total_weight > 0 else 0.0


def _weighted_quality(rows: list[ResearchAttributionAsset], total_weight: float) -> float:
    if not rows:
        return 0.0
    total = 0.0
    for row in rows:
        total += _number(row.data_quality_score) * _normalized_weight_by_row(row, total_weight, len(rows)) / 100
    return _round(total, 2)


def _contributors(rows: list[ResearchAttributionAsset], *, reverse: bool) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: _number(row.contribution_pct), reverse=reverse)
    selected = [row for row in ordered if (_number(row.contribution_pct) > 0 if reverse else _number(row.contribution_pct) < 0)]
    return [
        {
            "ticker": row.ticker,
            "assetName": row.asset_name,
            "contributionPct": _round(_number(row.contribution_pct), 4),
            "totalReturnPct": _round(_number(row.total_return_pct), 4),
            "weight": _round(_number(row.target_weight), 4),
        }
        for row in selected[:5]
    ]


def _summary(run: ResearchAttributionRun, top: list[dict[str, Any]], detractors: list[dict[str, Any]], benchmark_configured: bool) -> str:
    result = _number(run.portfolio_return_pct)
    lead = top[0]["ticker"] if top else "nenhum ativo positivo"
    drag = detractors[0]["ticker"] if detractors else "sem detrator relevante"
    benchmark = (
        f" Contra {run.benchmark_name}, o excesso foi de {_number(run.excess_return_pct):.2f}%."
        if benchmark_configured
        else " Benchmark ainda nao configurado para esta leitura."
    )
    return (
        f"A carteira-modelo teve atribuicao estimada de {result:.2f}% no periodo. "
        f"Principal contribuicao: {lead}. Principal detrator: {drag}.{benchmark} "
        "A leitura depende da qualidade dos historicos disponiveis no Market Data Engine."
    )


def _asset_row_to_dict(row: ResearchAttributionAsset) -> dict[str, Any]:
    return {
        "id": row.id,
        "runId": row.run_id,
        "assetId": row.asset_id,
        "ticker": row.ticker,
        "assetName": row.asset_name,
        "assetClass": row.asset_class,
        "sector": row.sector,
        "targetWeight": _round(_number(row.target_weight), 4),
        "startPrice": _round(_number(row.start_price), 6),
        "endPrice": _round(_number(row.end_price), 6),
        "priceReturnPct": _round(_number(row.price_return_pct), 4),
        "incomeReturnPct": _round(_number(row.income_return_pct), 4),
        "totalReturnPct": _round(_number(row.total_return_pct), 4),
        "contributionPct": _round(_number(row.contribution_pct), 4),
        "dataQualityScore": _round(_number(row.data_quality_score), 2),
        "provider": row.provider,
        "sourceType": row.source_type,
        "status": row.status,
        "evidenceIds": _json_load(row.evidence_ids_json, []),
        "metadata": _json_load(row.metadata_json, {}),
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def _parse_price_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        number = float(value)
        return number if isfinite(number) else 0.0
    except Exception:
        return 0.0


def _decimal(value: Any) -> Decimal:
    return Decimal(str(round(_number(value), 6)))


def _round(value: float, digits: int = 2) -> float:
    return round(_number(value), digits)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_load(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw or "")
    except Exception:
        return fallback


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in values:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
