from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncomeClassification:
    key: str
    label: str
    category: str
    taxable_note: str


DIVIDEND = IncomeClassification(
    key="dividend",
    label="Dividendo",
    category="provento",
    taxable_note="Dividendos de acoes brasileiras sao tratados como proventos; regra tributaria pode mudar e deve ser validada.",
)
JCP = IncomeClassification(
    key="jcp",
    label="JCP",
    category="provento",
    taxable_note="Juros sobre capital proprio normalmente sofrem IR retido na fonte e devem ser acompanhados separados do dividendo.",
)
FII_INCOME = IncomeClassification(
    key="fii_income",
    label="Rendimento de FII",
    category="provento_imobiliario",
    taxable_note="Rendimentos de FIIs podem ser isentos para pessoa fisica quando atendem aos requisitos legais.",
)
OTHER_INCOME = IncomeClassification(
    key="other_income",
    label="Outro provento",
    category="provento",
    taxable_note="Tratamento tributario depende da natureza do rendimento.",
)

JCP_ALIASES = {"jcp", "juros_sobre_capital_proprio", "juros sobre capital proprio", "interest_on_equity"}
DIVIDEND_ALIASES = {"manual", "dividend", "dividendo", "dividendos", "brapi", "cvm", "b3"}
FII_ALIASES = {"fii", "fii_income", "rendimento_fii", "rendimento de fii", "rendimento_imobiliario"}


def normalize_income_type(source: str | None = None, asset_class: str | None = None) -> IncomeClassification:
    normalized_source = (source or "").strip().lower()
    normalized_class = (asset_class or "").strip().lower()
    if normalized_source in JCP_ALIASES:
        return JCP
    if normalized_source in FII_ALIASES:
        return FII_INCOME
    if "fii" in normalized_class or "reit" in normalized_class:
        return FII_INCOME
    if normalized_source in DIVIDEND_ALIASES or not normalized_source:
        return DIVIDEND
    return OTHER_INCOME


def empty_income_breakdown() -> dict:
    return {
        "dividend": 0.0,
        "jcp": 0.0,
        "fii_income": 0.0,
        "other_income": 0.0,
        "total_proceeds": 0.0,
    }


def add_income_to_breakdown(breakdown: dict, amount: float, source: str | None = None, asset_class: str | None = None) -> None:
    classification = normalize_income_type(source, asset_class)
    breakdown[classification.key] = round(float(breakdown.get(classification.key, 0.0)) + float(amount or 0), 2)
    breakdown["total_proceeds"] = round(float(breakdown.get("total_proceeds", 0.0)) + float(amount or 0), 2)
