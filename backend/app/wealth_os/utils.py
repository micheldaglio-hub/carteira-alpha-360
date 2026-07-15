from __future__ import annotations

from datetime import datetime
from math import log


def as_float(value, digits: int = 2) -> float:
    try:
        return round(float(value or 0), digits)
    except (TypeError, ValueError):
        return 0.0


def greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia."
    if hour < 18:
        return "Boa tarde."
    return "Boa noite."


def estimate_months_to_target(current_value: float, target_value: float, monthly_contribution: float, monthly_return_pct: float) -> int | None:
    if target_value <= current_value:
        return 0
    monthly_return = monthly_return_pct / 100
    if monthly_contribution <= 0 and monthly_return <= 0:
        return None
    if monthly_return <= 0:
        return int((target_value - current_value + monthly_contribution - 1) // monthly_contribution)
    denominator = current_value + monthly_contribution / monthly_return
    numerator = target_value + monthly_contribution / monthly_return
    if denominator <= 0 or numerator <= 0 or numerator <= denominator:
        return None
    months = log(numerator / denominator) / log(1 + monthly_return)
    return max(0, int(round(months)))


def required_monthly_contribution(current_value: float, target_value: float, months: int, monthly_return_pct: float) -> float | None:
    if months <= 0:
        return 0.0 if current_value >= target_value else None
    monthly_return = monthly_return_pct / 100
    if monthly_return <= 0:
        return round(max(0, target_value - current_value) / months, 2)
    future_current = current_value * ((1 + monthly_return) ** months)
    factor = (((1 + monthly_return) ** months) - 1) / monthly_return
    if factor <= 0:
        return None
    return round(max(0, target_value - future_current) / factor, 2)


def status_from_score(score: float) -> str:
    if score >= 80:
        return "forte"
    if score >= 65:
        return "saudavel"
    if score >= 50:
        return "acompanhar"
    return "requer_plano"

