from __future__ import annotations

from datetime import date, datetime, time

from app.services.scoring import band, clamp, inverse_band


def score_status(score: float) -> str:
    if score >= 82:
        return "Excelente"
    if score >= 68:
        return "Saudavel"
    if score >= 52:
        return "Monitorar"
    if score >= 38:
        return "Atencao"
    return "Critico"


def severity_from_score(score: float) -> str:
    if score >= 68:
        return "info"
    if score >= 52:
        return "warning"
    return "critical"


def weighted_average(items: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in items)
    if total_weight <= 0:
        return 0.0
    return round(sum(value * weight for value, weight in items) / total_weight, 2)


def average(values: list[float], fallback: float = 0.0) -> float:
    if not values:
        return fallback
    return round(sum(values) / len(values), 2)


def date_to_datetime(day: date) -> datetime:
    return datetime.combine(day, time.min)


def iso(value: datetime | date | None) -> str:
    if value is None:
        return datetime.utcnow().isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return date_to_datetime(value).isoformat()


def money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percent(value: float) -> str:
    return f"{value:.2f}%".replace(".", ",")
