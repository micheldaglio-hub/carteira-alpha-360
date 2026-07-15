from __future__ import annotations

from sqlalchemy.orm import Session

from app.alpha.contracts import HealthReport, HealthScore
from app.alpha.utils import average, band, clamp, percent, score_status, weighted_average
from app.services.portfolio import get_allocations, get_dashboard, get_positions
from app.services.scoring import list_scores


CLASS_LIQUIDITY = {
    "Acoes": 84,
    "ETFs": 88,
    "FIIs": 72,
    "Renda fixa": 80,
    "Cripto": 62,
}


def _score(nome: str, nota: float, justificativa: str) -> HealthScore:
    normalized = round(clamp(nota), 2)
    return HealthScore(nome=nome, nota=normalized, status=score_status(normalized), justificativa=justificativa)


def calculate_health(db: Session, user_id: str) -> HealthReport:
    positions = get_positions(db, user_id)
    dashboard = get_dashboard(db, user_id)
    allocations = get_allocations(positions)
    score_rows = list_scores(db)
    score_by_asset = {row["assetId"]: row for row in score_rows}

    total_equity = dashboard["metrics"]["totalEquity"]
    asset_count = len(positions)
    class_count = len({position["class"] for position in positions})
    sector_count = len({position["sector"] for position in positions})
    largest_asset = max((position["weight"] for position in positions), default=0)
    largest_sector = max((row["weight"] for row in allocations["bySector"]), default=0)

    diversification = (
        band(asset_count, 2, 12) * 0.45
        + band(class_count, 1, 4) * 0.25
        + band(sector_count, 1, 8) * 0.30
    )
    concentration = 100 - max(0, largest_asset - 15) * 2.2 - max(0, largest_sector - 30) * 1.4
    liquidity = weighted_average(
        [(CLASS_LIQUIDITY.get(position["class"], 62), position["currentValue"]) for position in positions]
    )

    dy_on_avg = weighted_average(
        [(position["dividendYieldOnAvg"], position["investedValue"]) for position in positions]
    )
    annual_income_yield = (
        dashboard["metrics"]["projectedPassiveIncome"] * 12 / total_equity * 100 if total_equity else 0
    )
    dividend_quality = band(dy_on_avg, 1, 8) * 0.55 + band(annual_income_yield, 2, 10) * 0.45

    held_scores = [score_by_asset[position["assetId"]] for position in positions if position["assetId"] in score_by_asset]
    growth = average([row["scoreCrescimento"] for row in held_scores], fallback=52)
    safety = average([row["scoreSeguranca"] for row in held_scores], fallback=52)
    valuation = average([row["scoreValuation"] for row in held_scores], fallback=52)
    volatility = 100 - average([row["scoreRisco"] for row in held_scores], fallback=48)
    passive_income = band(annual_income_yield, 2, 11) * 0.7 + band(dashboard["metrics"]["dividendsYear"], 200, 4000) * 0.3
    general_quality = average([dividend_quality, growth, safety, valuation, volatility], fallback=52)

    scores = [
        _score(
            "Diversificacao",
            diversification,
            f"{asset_count} ativos, {class_count} classes e {sector_count} setores compoem a carteira.",
        ),
        _score(
            "Concentracao",
            concentration,
            f"Maior ativo em {percent(largest_asset)} e maior setor em {percent(largest_sector)}.",
        ),
        _score(
            "Liquidez",
            liquidity,
            "Nota estimada pela classe dos ativos e pelo peso financeiro de cada posicao.",
        ),
        _score(
            "Proventos",
            dividend_quality,
            f"DY sobre preco medio em {percent(dy_on_avg)} e renda anual projetada em {percent(annual_income_yield)} do patrimonio.",
        ),
        _score("Crescimento", growth, "Media dos scores de crescimento dos ativos em carteira."),
        _score("Seguranca", safety, "Media de alavancagem, recorrencia de lucro e estabilidade setorial."),
        _score("Valuation", valuation, "Media de leitura relativa de P/L, P/VP e parametros de valor."),
        _score("Volatilidade", volatility, "Estimativa inversa do risco agregado dos ativos carregados."),
        _score(
            "Renda Passiva",
            passive_income,
            "Nota baseada na renda mensal projetada e nos proventos recebidos no ano.",
        ),
        _score("Qualidade Geral", general_quality, "Sintese de proventos, crescimento, seguranca, valuation e volatilidade."),
    ]
    score_map = {item.nome: item.nota for item in scores}
    overall = weighted_average(
        [
            (score_map["Diversificacao"], 0.12),
            (score_map["Concentracao"], 0.13),
            (score_map["Liquidez"], 0.08),
            (score_map["Proventos"], 0.13),
            (score_map["Crescimento"], 0.11),
            (score_map["Seguranca"], 0.13),
            (score_map["Valuation"], 0.09),
            (score_map["Volatilidade"], 0.08),
            (score_map["Renda Passiva"], 0.07),
            (score_map["Qualidade Geral"], 0.06),
        ]
    )
    return HealthReport(notaGeral=round(clamp(overall), 2), status=score_status(overall), scores=scores)
