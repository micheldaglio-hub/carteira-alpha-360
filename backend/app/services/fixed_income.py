from __future__ import annotations

import re
import time
from datetime import date, timedelta
from decimal import Decimal
from threading import Lock
from typing import Any

import httpx

from app.core.config import get_settings


BCB_CDI_DAILY_SERIES = "12"
FALLBACK_CDI_DAILY_PCT = Decimal("0.047")
CDI_CACHE_TTL_SECONDS = 300
_CDI_RATE_CACHE: dict[tuple[date, date], tuple[float, list[dict[str, Any]]]] = {}
_CDI_RATE_CACHE_LOCK = Lock()


def is_fixed_income_class(asset_class: str | None) -> bool:
    raw = (asset_class or "").strip().lower()
    return any(term in raw for term in ["renda fixa", "fixed income", "cdb", "rdb", "tesouro"])


def parse_cdi_percent(*parts: str | None) -> Decimal:
    text = " ".join(part or "" for part in parts).lower()
    match = re.search(r"(\d+(?:[\.,]\d+)?)\s*%?\s*(?:do\s*)?cdi", text)
    if match:
        return Decimal(match.group(1).replace(",", "."))
    if "cdi" in text:
        return Decimal("100")
    return Decimal("100")


def fetch_cdi_daily_rates(start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
    end = end_date or date.today()
    if start_date > end:
        return []
    cache_key = (start_date, end)
    now = time.monotonic()
    with _CDI_RATE_CACHE_LOCK:
        cached = _CDI_RATE_CACHE.get(cache_key)
        if cached and now - cached[0] < CDI_CACHE_TTL_SECONDS:
            return list(cached[1])

    settings = get_settings()
    base_url = settings.bcb_sgs_base_url.rstrip("/")
    url = f"{base_url}/bcdata.sgs.{BCB_CDI_DAILY_SERIES}/dados"
    params = {
        "formato": "json",
        "dataInicial": start_date.strftime("%d/%m/%Y"),
        "dataFinal": end.strftime("%d/%m/%Y"),
    }
    try:
        with httpx.Client(timeout=6.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            rows = response.json()
    except Exception:
        with _CDI_RATE_CACHE_LOCK:
            _CDI_RATE_CACHE[cache_key] = (now, [])
        raise

    parsed = []
    for row in rows if isinstance(rows, list) else []:
        try:
            day, month, year = str(row.get("data", "")).split("/")
            parsed.append(
                {
                    "date": date(int(year), int(month), int(day)),
                    "dailyPct": Decimal(str(row.get("valor", "0")).replace(",", ".")),
                    "source": "Banco Central SGS 12",
                }
            )
        except Exception:
            continue
    result = sorted(parsed, key=lambda item: item["date"])
    with _CDI_RATE_CACHE_LOCK:
        _CDI_RATE_CACHE[cache_key] = (now, result)
    return list(result)


def accrue_cdi_lots(
    lots: list[dict[str, Any]],
    *,
    cdi_percent: Decimal,
    end_date: date | None = None,
    rates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    end = end_date or date.today()
    clean_lots = [
        {"date": _as_date(lot.get("date"), end), "amount": Decimal(str(lot.get("amount") or "0"))}
        for lot in lots
        if Decimal(str(lot.get("amount") or "0")) > 0
    ]
    if not clean_lots:
        return _empty_result(cdi_percent)

    first_date = min(lot["date"] for lot in clean_lots)
    rate_rows = rates if rates is not None else _safe_fetch_rates(first_date, end)
    source = "Banco Central SGS 12" if rate_rows else "fallback CDI estimado"
    rate_by_date = {row["date"]: Decimal(str(row["dailyPct"])) for row in rate_rows}

    invested = sum(lot["amount"] for lot in clean_lots)
    current = Decimal("0")
    applied_days = 0
    last_daily_pct = FALLBACK_CDI_DAILY_PCT

    for lot in clean_lots:
        value = lot["amount"]
        day = lot["date"] + timedelta(days=1)
        while day <= end:
            daily_pct = rate_by_date.get(day)
            if daily_pct is not None:
                last_daily_pct = daily_pct
                applied_days += 1
            elif day.weekday() < 5 and not rate_rows:
                daily_pct = FALLBACK_CDI_DAILY_PCT
                applied_days += 1
            else:
                daily_pct = None
            if daily_pct is not None:
                value *= Decimal("1") + ((daily_pct * cdi_percent / Decimal("100")) / Decimal("100"))
            day += timedelta(days=1)
        current += value

    pnl = current - invested
    return {
        "indexer": "CDI",
        "cdiPercent": float(cdi_percent),
        "source": source,
        "dailyRatePct": float(last_daily_pct),
        "appliedDays": applied_days,
        "investedValue": round(float(invested), 2),
        "currentValue": round(float(current), 2),
        "pnl": round(float(pnl), 2),
        "returnPct": round(float((pnl / invested * Decimal("100")) if invested else Decimal("0")), 2),
        "reading": (
            f"Renda fixa pos-fixada estimada por CDI diario acumulado a {float(cdi_percent):.2f}% do CDI. "
            "O valor e estimativo ate a integracao direta com a instituicao financeira."
        ),
    }


def _safe_fetch_rates(start_date: date, end_date: date) -> list[dict[str, Any]]:
    try:
        return fetch_cdi_daily_rates(start_date, end_date)
    except Exception:
        return []


def _as_date(value: Any, fallback: date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return fallback


def _empty_result(cdi_percent: Decimal) -> dict[str, Any]:
    return {
        "indexer": "CDI",
        "cdiPercent": float(cdi_percent),
        "source": "sem_lotes",
        "dailyRatePct": 0,
        "appliedDays": 0,
        "investedValue": 0,
        "currentValue": 0,
        "pnl": 0,
        "returnPct": 0,
        "reading": "Sem lotes de renda fixa para atualizar.",
    }
