from __future__ import annotations

import json
import math
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import MarketDataCacheEntry, MarketDataProviderEvent
from app.services.market_data.v2.providers.bcb import BCB_SGS_FX_CODES
from app.services.portfolio import get_allocations, get_positions
from app.wealth_os.contracts import (
    DataConfidenceItem,
    FxRateSnapshot,
    MacroFxSnapshot,
    MacroIndicator,
    MacroPortfolioReading,
)


MACRO_CACHE_PREFIX = "wealth-os:macro-fx:v1"
MACRO_TTL_SECONDS = 60 * 60 * 6
FX_TTL_SECONDS = 60 * 15

BCB_MACRO_SERIES = {
    "selic_meta": {
        "code": "432",
        "title": "Selic meta",
        "unit": "% a.a.",
        "period": "ultimo dado",
        "window": 6,
        "kind": "latest",
    },
    "ipca_mensal": {
        "code": "433",
        "title": "IPCA mensal",
        "unit": "% m.m.",
        "period": "ultimo mes",
        "window": 6,
        "kind": "latest",
    },
    "ipca_12m": {
        "code": "433",
        "title": "IPCA acumulado 12m",
        "unit": "% a.a.",
        "period": "12 meses",
        "window": 12,
        "kind": "compound_percent",
    },
}

DEFAULT_FX_PAIRS = (("USD", "BRL"), ("EUR", "BRL"))


class EconomicMacroFxEngine:
    """Builds the real macro and FX layer consumed by Wealth OS.

    The engine keeps provider calls behind the backend, writes mandatory cache
    rows, and never makes the UI depend directly on an external provider.
    """

    def __init__(self, client_factory: Callable[[], httpx.Client] | None = None) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.bcb_sgs_base_url.rstrip("/")
        self.client_factory = client_factory or (lambda: httpx.Client(timeout=6.0))

    def build_snapshot(self, db: Session, user_id: str, *, refresh: bool = False) -> MacroFxSnapshot:
        indicators = [self._get_macro_indicator(db, indicator_id, refresh=refresh) for indicator_id in BCB_MACRO_SERIES]
        fx_rates = [self._get_fx_rate(db, base, quote, refresh=refresh) for base, quote in DEFAULT_FX_PAIRS]
        readings = self._build_portfolio_readings(db, user_id, indicators, fx_rates)
        source_health = self._build_source_health(indicators, fx_rates)
        warnings = sorted({warning for item in [*indicators, *fx_rates] for warning in item.warnings})
        status = "real_time" if all(item.qualityScore >= 70 for item in [*indicators, *fx_rates]) else "parcial"

        headline = "Macro e cambio carregados com dados reais do Banco Central."
        if status == "parcial":
            headline = "Macro e cambio carregados com dados reais, cache ou fallback quando a fonte oscilou."

        return MacroFxSnapshot(
            status=status,
            headline=headline,
            updatedAt=_utcnow().isoformat(),
            indicators=indicators,
            fxRates=fx_rates,
            portfolioReadings=readings,
            sourceHealth=source_health,
            warnings=warnings,
        )

    def _get_macro_indicator(self, db: Session, indicator_id: str, *, refresh: bool) -> MacroIndicator:
        spec = BCB_MACRO_SERIES[indicator_id]
        cache_key = f"{MACRO_CACHE_PREFIX}:macro:{indicator_id}"
        cached = None if refresh else _load_cache(db, cache_key, allow_expired=False)
        if cached:
            return _macro_indicator_from_dict(cached, "cache_hit")

        try:
            rows = self._fetch_sgs_series(spec["code"], int(spec["window"]))
            indicator = self._normalize_macro_indicator(indicator_id, spec, rows)
            _save_cache(db, cache_key, asdict(indicator), provider="bcb_sgs", data_type="macro_indicator", ttl_seconds=MACRO_TTL_SECONDS)
            return indicator
        except Exception as exc:
            _record_provider_failure(db, "bcb_sgs", exc)
            stale = _load_cache(db, cache_key, allow_expired=True)
            if stale:
                return _macro_indicator_from_dict(stale, "stale_cache", "provider_unavailable")
            return MacroIndicator(
                id=indicator_id,
                title=str(spec["title"]),
                value=0,
                unit=str(spec["unit"]),
                period=str(spec["period"]),
                trend="indisponivel",
                status="indisponivel",
                source="Banco Central SGS",
                sourceCode=str(spec["code"]),
                asOf=_utcnow().isoformat(),
                qualityScore=0,
                reading="Fonte macro indisponivel agora e sem cache anterior para este indicador.",
                warnings=["provider_unavailable", "empty_cache"],
            )

    def _get_fx_rate(self, db: Session, base: str, quote: str, *, refresh: bool) -> FxRateSnapshot:
        pair = f"{base}/{quote}"
        code = BCB_SGS_FX_CODES.get((base, quote))
        invert = False
        if code is None:
            code = BCB_SGS_FX_CODES.get((quote, base))
            invert = True
        cache_key = f"{MACRO_CACHE_PREFIX}:fx:{base}:{quote}"
        cached = None if refresh else _load_cache(db, cache_key, allow_expired=False)
        if cached:
            return _fx_rate_from_dict(cached, "cache_hit")

        if code is None:
            return FxRateSnapshot(
                pair=pair,
                baseCurrency=base,
                quoteCurrency=quote,
                rate=0,
                source="Banco Central SGS",
                sourceCode="",
                asOf=_utcnow().isoformat(),
                status="par_nao_suportado",
                qualityScore=0,
                reading=f"Par {pair} ainda nao esta mapeado no SGS.",
                warnings=["unsupported_pair"],
            )

        try:
            rows = self._fetch_sgs_series(code, 1)
            row = rows[-1]
            rate = _safe_float(row.get("valor"))
            if invert and rate:
                rate = 1 / rate
            snapshot = FxRateSnapshot(
                pair=pair,
                baseCurrency=base,
                quoteCurrency=quote,
                rate=round(rate, 6),
                source="Banco Central SGS",
                sourceCode=str(code),
                asOf=_parse_bcb_date(row.get("data")).isoformat(),
                status="atualizado",
                qualityScore=86 if rate > 0 else 30,
                reading=f"{pair} em {quote}: {rate:.4f}.",
                warnings=[] if rate > 0 else ["zero_rate"],
            )
            _save_cache(db, cache_key, asdict(snapshot), provider="bcb_sgs", data_type="fx_rate", ttl_seconds=FX_TTL_SECONDS)
            return snapshot
        except Exception as exc:
            _record_provider_failure(db, "bcb_sgs", exc)
            stale = _load_cache(db, cache_key, allow_expired=True)
            if stale:
                return _fx_rate_from_dict(stale, "stale_cache", "provider_unavailable")
            return FxRateSnapshot(
                pair=pair,
                baseCurrency=base,
                quoteCurrency=quote,
                rate=0,
                source="Banco Central SGS",
                sourceCode=str(code),
                asOf=_utcnow().isoformat(),
                status="indisponivel",
                qualityScore=0,
                reading=f"Cambio {pair} indisponivel agora e sem cache anterior.",
                warnings=["provider_unavailable", "empty_cache"],
            )

    def _fetch_sgs_series(self, code: str, last: int) -> list[dict[str, Any]]:
        with self.client_factory() as client:
            response = client.get(f"{self.base_url}/bcdata.sgs.{code}/dados/ultimos/{last}", params={"formato": "json"})
            response.raise_for_status()
            rows = response.json()
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"SGS {code} sem dados")
        return sorted(rows, key=lambda row: _parse_bcb_date(row.get("data")))

    def _normalize_macro_indicator(self, indicator_id: str, spec: dict[str, Any], rows: list[dict[str, Any]]) -> MacroIndicator:
        values = [_safe_float(row.get("valor")) for row in rows if row.get("valor") not in (None, "")]
        if not values:
            raise ValueError(f"SGS {spec['code']} sem valores numericos")
        latest_row = rows[-1]
        latest = values[-1]
        if spec["kind"] == "compound_percent":
            value = _compound_percent(values[-12:])
        else:
            value = latest
        previous = values[-2] if len(values) > 1 else latest
        trend = _trend(value, previous)
        status = _indicator_status(indicator_id, value)
        reading = _indicator_reading(indicator_id, value, trend, status)
        quality = 92 if indicator_id != "ipca_12m" or len(values) >= 12 else 72
        return MacroIndicator(
            id=indicator_id,
            title=str(spec["title"]),
            value=round(value, 4),
            unit=str(spec["unit"]),
            period=str(spec["period"]),
            trend=trend,
            status=status,
            source="Banco Central SGS",
            sourceCode=str(spec["code"]),
            asOf=_parse_bcb_date(latest_row.get("data")).isoformat(),
            qualityScore=quality,
            reading=reading,
            warnings=[] if quality >= 80 else ["short_history"],
        )

    def _build_portfolio_readings(
        self,
        db: Session,
        user_id: str,
        indicators: list[MacroIndicator],
        fx_rates: list[FxRateSnapshot],
    ) -> list[MacroPortfolioReading]:
        positions = get_positions(db, user_id)
        allocations = get_allocations(positions)
        sectors = ", ".join(item["name"] for item in allocations.get("bySector", [])[:4]) or "setores ainda pouco classificados"
        classes = ", ".join(item["name"] for item in allocations.get("byClass", [])[:4]) or "classes ainda pouco classificadas"
        by_indicator = {item.id: item for item in indicators}
        selic = by_indicator.get("selic_meta")
        ipca = by_indicator.get("ipca_12m")
        usd = next((item for item in fx_rates if item.pair == "USD/BRL"), None)

        selic_value = selic.value if selic else 0
        ipca_value = ipca.value if ipca else 0
        usd_rate = usd.rate if usd else 0

        if selic_value >= 12:
            interest_severity = "alta"
            interest_reading = "Juros altos aumentam o custo de capital e tornam valuation mais exigente."
            interest_impact = f"Classes monitoradas: {classes}. Bancos, seguradoras e caixa tendem a reagir diferente de crescimento e FIIs."
        elif selic_value > 0:
            interest_severity = "moderada"
            interest_reading = "Juros em faixa monitoravel: ainda impactam valuation, mas sem leitura extrema pelo motor."
            interest_impact = f"Classes monitoradas: {classes}."
        else:
            interest_severity = "dados_parciais"
            interest_reading = "Sem Selic atual validada no momento."
            interest_impact = "A leitura usa cache/fallback ate a fonte macro voltar."

        if ipca_value >= 5:
            inflation_severity = "alta"
            inflation_reading = "Inflacao acima do centro de referencia exige atencao a margem, reajuste de contratos e ganho real."
        elif ipca_value > 0:
            inflation_severity = "moderada"
            inflation_reading = "Inflacao monitorada: o sistema acompanha se o patrimonio cresce acima do poder de compra."
        else:
            inflation_severity = "dados_parciais"
            inflation_reading = "Sem IPCA 12m atual validado no momento."

        fx_severity = "moderada" if usd_rate > 0 else "dados_parciais"
        fx_reading = "Cambio USD/BRL monitorado para patrimonio global, stocks, ETFs internacionais, BDRs e cripto."
        fx_impact = "A carteira ainda precisa classificar moedas por ativo para medir protecao cambial com precisao total."

        return [
            MacroPortfolioReading(
                id="interest_rate_sensitivity",
                title="Sensibilidade a juros",
                severity=interest_severity,
                reading=interest_reading,
                portfolioImpact=interest_impact,
                dataUsed=["Banco Central SGS 432", f"Classes: {classes}"],
            ),
            MacroPortfolioReading(
                id="inflation_sensitivity",
                title="Sensibilidade a inflacao",
                severity=inflation_severity,
                reading=inflation_reading,
                portfolioImpact=f"Setores monitorados: {sectors}. Energia, saneamento, FIIs e empresas reguladas exigem leitura de repasse.",
                dataUsed=["Banco Central SGS 433", f"Setores: {sectors}"],
            ),
            MacroPortfolioReading(
                id="fx_exposure",
                title="Exposicao cambial",
                severity=fx_severity,
                reading=fx_reading,
                portfolioImpact=fx_impact,
                dataUsed=[f"USD/BRL {usd_rate:.4f}" if usd_rate else "USD/BRL indisponivel", "Asset Engine Universal"],
            ),
        ]

    def _build_source_health(self, indicators: list[MacroIndicator], fx_rates: list[FxRateSnapshot]) -> list[DataConfidenceItem]:
        macro_quality = _average([item.qualityScore for item in indicators])
        fx_quality = _average([item.qualityScore for item in fx_rates])
        macro_status = "confiavel" if macro_quality >= 80 else "parcial" if macro_quality > 0 else "indisponivel"
        fx_status = "confiavel" if fx_quality >= 80 else "parcial" if fx_quality > 0 else "indisponivel"
        return [
            DataConfidenceItem(
                area="Macro Brasil",
                status=macro_status,
                confidenceScore=macro_quality,
                source="Banco Central SGS",
                reading="Selic e IPCA carregados por API publica do Banco Central com cache obrigatorio.",
                nextStep="Adicionar historico persistente e curvas futuras quando houver provedor apropriado.",
            ),
            DataConfidenceItem(
                area="Cambio",
                status=fx_status,
                confidenceScore=fx_quality,
                source="Banco Central SGS",
                reading="Pares USD/BRL e EUR/BRL tratados no backend, com fallback para cache.",
                nextStep="Adicionar AwesomeAPI/Twelve Data como fallback futuro e cambio historico para backtests globais.",
            ),
        ]


def build_macro_fx_snapshot(db: Session, user_id: str, *, refresh: bool = False) -> MacroFxSnapshot:
    return EconomicMacroFxEngine().build_snapshot(db, user_id, refresh=refresh)


def _load_cache(db: Session, cache_key: str, *, allow_expired: bool) -> dict[str, Any] | None:
    row = db.execute(select(MarketDataCacheEntry).where(MarketDataCacheEntry.cache_key == cache_key)).scalar_one_or_none()
    if row is None:
        return None
    if not allow_expired and _is_expired(row.expires_at):
        return None
    try:
        payload = json.loads(row.payload_json)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _save_cache(
    db: Session,
    cache_key: str,
    payload: dict[str, Any],
    *,
    provider: str,
    data_type: str,
    ttl_seconds: int,
) -> None:
    row = db.execute(select(MarketDataCacheEntry).where(MarketDataCacheEntry.cache_key == cache_key)).scalar_one_or_none()
    if row is None:
        row = MarketDataCacheEntry(cache_key=cache_key)
        db.add(row)
    row.provider = provider
    row.data_type = data_type
    row.payload_json = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    row.quality_score = Decimal(str(float(payload.get("qualityScore") or 0)))
    row.expires_at = _utcnow() + timedelta(seconds=ttl_seconds)
    row.updated_at = _utcnow()
    _flush_and_commit_cache(db)


def _record_provider_failure(db: Session, provider: str, exc: Exception) -> None:
    status_code = str(getattr(exc, "status_code", "") or "")
    try:
        db.add(
            MarketDataProviderEvent(
                provider=provider,
                event_type=exc.__class__.__name__,
                severity="warning",
                message=str(exc)[:2000],
                status_code=status_code,
            )
        )
        _flush_and_commit_cache(db)
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def _flush_and_commit_cache(db: Session) -> None:
    try:
        db.flush()
        db.commit()
    except Exception:
        db.rollback()


def _macro_indicator_from_dict(payload: dict[str, Any], *warnings: str) -> MacroIndicator:
    existing = list(payload.get("warnings") or [])
    merged = [*existing, *[warning for warning in warnings if warning]]
    return MacroIndicator(
        id=str(payload.get("id") or ""),
        title=str(payload.get("title") or ""),
        value=_safe_float(payload.get("value")),
        unit=str(payload.get("unit") or ""),
        period=str(payload.get("period") or ""),
        trend=str(payload.get("trend") or "estavel"),
        status=str(payload.get("status") or "cache"),
        source=str(payload.get("source") or "Banco Central SGS"),
        sourceCode=str(payload.get("sourceCode") or ""),
        asOf=str(payload.get("asOf") or _utcnow().isoformat()),
        qualityScore=_safe_float(payload.get("qualityScore")),
        reading=str(payload.get("reading") or ""),
        warnings=sorted(set(merged)),
    )


def _fx_rate_from_dict(payload: dict[str, Any], *warnings: str) -> FxRateSnapshot:
    existing = list(payload.get("warnings") or [])
    merged = [*existing, *[warning for warning in warnings if warning]]
    return FxRateSnapshot(
        pair=str(payload.get("pair") or ""),
        baseCurrency=str(payload.get("baseCurrency") or ""),
        quoteCurrency=str(payload.get("quoteCurrency") or ""),
        rate=_safe_float(payload.get("rate")),
        source=str(payload.get("source") or "Banco Central SGS"),
        sourceCode=str(payload.get("sourceCode") or ""),
        asOf=str(payload.get("asOf") or _utcnow().isoformat()),
        status=str(payload.get("status") or "cache"),
        qualityScore=_safe_float(payload.get("qualityScore")),
        reading=str(payload.get("reading") or ""),
        warnings=sorted(set(merged)),
    )


def _indicator_status(indicator_id: str, value: float) -> str:
    if value <= 0:
        return "indisponivel"
    if indicator_id == "selic_meta":
        if value >= 12:
            return "juros_altos"
        if value >= 8:
            return "juros_neutros_altos"
        return "juros_mais_baixos"
    if indicator_id == "ipca_12m":
        if value >= 5:
            return "inflacao_pressionada"
        if value >= 3:
            return "inflacao_monitorada"
        return "inflacao_baixa"
    if indicator_id == "ipca_mensal":
        if value >= 0.6:
            return "pressao_mensal"
        if value >= 0:
            return "normal"
        return "deflacao"
    return "monitorado"


def _indicator_reading(indicator_id: str, value: float, trend: str, status: str) -> str:
    if indicator_id == "selic_meta":
        return f"Selic em {value:.2f}% a.a.; leitura {status.replace('_', ' ')} e tendencia {trend}."
    if indicator_id == "ipca_12m":
        return f"IPCA acumulado em {value:.2f}% em 12 meses; leitura {status.replace('_', ' ')}."
    if indicator_id == "ipca_mensal":
        return f"IPCA mensal em {value:.2f}%; tendencia {trend} no ultimo dado."
    return f"Indicador em {value:.2f}."


def _trend(current: float, previous: float) -> str:
    delta = current - previous
    if abs(delta) < 0.05:
        return "estavel"
    return "alta" if delta > 0 else "queda"


def _compound_percent(values: list[float]) -> float:
    if not values:
        return 0
    factor = math.prod(1 + value / 100 for value in values)
    return (factor - 1) * 100


def _average(values: list[float]) -> float:
    usable = [value for value in values if value > 0]
    if not usable:
        return 0
    return round(sum(usable) / len(usable), 2)


def _safe_float(value: Any, default: float = 0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _parse_bcb_date(value: Any) -> datetime:
    if not value:
        return _utcnow()
    try:
        return datetime.strptime(str(value), "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return _utcnow()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    return expires_at <= _utcnow()
