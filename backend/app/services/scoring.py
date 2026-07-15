from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Asset, MarketSnapshot


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def band(value: float, low: float, high: float) -> float:
    if high == low:
        return 0
    return clamp((value - low) / (high - low) * 100)


def inverse_band(value: float, low: float, high: float) -> float:
    return 100 - band(value, low, high)


def classification(score: float) -> str:
    if score >= 82:
        return "Excelente"
    if score >= 68:
        return "Bom"
    if score >= 52:
        return "Neutro"
    if score >= 38:
        return "Atencao"
    return "Evitar"


def market_term(final_score: float, valuation_score: float, dividend_score: float, growth_score: float) -> str:
    if final_score < 40:
        return "Fora dos criterios"
    if valuation_score >= 72 and final_score >= 65:
        return "Ativo descontado"
    if valuation_score <= 35 and final_score >= 55:
        return "Ativo caro"
    if dividend_score >= 72 and dividend_score >= growth_score:
        return "Bom para proventos"
    if growth_score >= 72:
        return "Bom para crescimento"
    if final_score >= 68:
        return "Ativo atrativo"
    return "Atencao ao risco"


def _float(value) -> float:
    return float(value or 0)


def dividend_score(snapshot: MarketSnapshot) -> tuple[float, list[str]]:
    dy = _float(snapshot.dividend_yield)
    payout = _float(snapshot.payout)
    debt = _float(snapshot.debt_to_ebitda)
    consistency = _float(snapshot.dividend_consistency)
    recurring = _float(snapshot.recurring_profit)
    stability = _float(snapshot.sector_stability)
    frequency = float(snapshot.payment_frequency or 0)

    payout_score = 100 if 35 <= payout <= 80 else inverse_band(abs(payout - 58), 0, 80)
    score = (
        band(dy, 2, 11) * 0.25
        + band(frequency, 2, 12) * 0.15
        + consistency * 0.18
        + payout_score * 0.14
        + recurring * 0.12
        + inverse_band(debt, 0, 5) * 0.09
        + stability * 0.07
    )
    reasons = [
        f"DY atual em {dy:.2f}% com frequencia de {int(frequency)} pagamentos/ano.",
        f"Consistencia historica estimada em {consistency:.0f}/100 e payout em {payout:.1f}%.",
        f"Risco de corte acompanha divida liquida/EBITDA de {debt:.1f}x e estabilidade setorial.",
    ]
    return round(clamp(score), 2), reasons


def growth_score(snapshot: MarketSnapshot) -> tuple[float, list[str]]:
    revenue = _float(snapshot.revenue_growth)
    profit = _float(snapshot.profit_growth)
    margin = _float(snapshot.net_margin)
    roe = _float(snapshot.roe)
    roic = _float(snapshot.roic)
    debt = _float(snapshot.debt_to_ebitda)
    appreciation = _float(snapshot.historical_appreciation)
    consistency = _float(snapshot.recurring_profit)

    score = (
        band(revenue, -5, 25) * 0.17
        + band(profit, -8, 30) * 0.19
        + band(margin, 5, 32) * 0.13
        + band(roe, 5, 28) * 0.15
        + band(roic, 4, 24) * 0.14
        + inverse_band(debt, 0, 5) * 0.10
        + band(appreciation, -10, 80) * 0.07
        + consistency * 0.05
    )
    reasons = [
        f"Receita cresce {revenue:.1f}% e lucro cresce {profit:.1f}% no recorte analisado.",
        f"Margem liquida de {margin:.1f}%, ROE de {roe:.1f}% e ROIC de {roic:.1f}%.",
        f"Consistencia operacional e alavancagem entram como filtros de qualidade.",
    ]
    return round(clamp(score), 2), reasons


def safety_score(snapshot: MarketSnapshot) -> float:
    return round(
        clamp(
            inverse_band(_float(snapshot.debt_to_ebitda), 0, 5) * 0.35
            + _float(snapshot.recurring_profit) * 0.25
            + _float(snapshot.sector_stability) * 0.25
            + _float(snapshot.dividend_consistency) * 0.15
        ),
        2,
    )


def valuation_score(snapshot: MarketSnapshot) -> float:
    pe = _float(snapshot.pe_ratio)
    pvp = _float(snapshot.pvp)
    pe_score = 75 if 6 <= pe <= 14 else inverse_band(abs(pe - 10), 0, 24)
    pvp_score = 80 if 0.7 <= pvp <= 1.4 else inverse_band(abs(pvp - 1.0), 0, 3)
    return round(clamp(pe_score * 0.58 + pvp_score * 0.42), 2)


def risk_score(snapshot: MarketSnapshot) -> float:
    raw_risk = (
        band(_float(snapshot.debt_to_ebitda), 0, 5) * 0.40
        + inverse_band(_float(snapshot.recurring_profit), 30, 95) * 0.25
        + inverse_band(_float(snapshot.sector_stability), 30, 95) * 0.20
        + inverse_band(_float(snapshot.dividend_consistency), 30, 95) * 0.15
    )
    return round(clamp(raw_risk), 2)


def _data_status(snapshot: MarketSnapshot) -> tuple[str, int]:
    fields = [
        snapshot.dividend_yield,
        snapshot.payout,
        snapshot.revenue_growth,
        snapshot.profit_growth,
        snapshot.net_margin,
        snapshot.roe,
        snapshot.roic,
        snapshot.debt_to_ebitda,
        snapshot.pe_ratio,
        snapshot.pvp,
    ]
    filled = sum(1 for value in fields if abs(_float(value)) > 0)
    return ("completo" if filled >= 5 else "parcial"), filled


def list_scores(db: Session, asset_ids: Iterable[str] | None = None) -> list[dict]:
    query = select(Asset).options(joinedload(Asset.snapshot)).order_by(Asset.ticker.asc())
    if asset_ids is not None:
        ids = list(asset_ids)
        if not ids:
            return []
        query = query.where(Asset.id.in_(ids))
    assets = db.execute(query).scalars().all()
    rows = []
    for asset in assets:
        if not asset.snapshot:
            continue
        data_status, filled_fields = _data_status(asset.snapshot)
        d_score, d_reasons = dividend_score(asset.snapshot)
        g_score, g_reasons = growth_score(asset.snapshot)
        sec_score = safety_score(asset.snapshot)
        val_score = valuation_score(asset.snapshot)
        r_score = risk_score(asset.snapshot)
        final_score = round(
            d_score * 0.24 + g_score * 0.24 + sec_score * 0.22 + val_score * 0.18 + (100 - r_score) * 0.12,
            2,
        )
        asset_classification = classification(final_score)
        asset_term = market_term(final_score, val_score, d_score, g_score)
        if data_status == "parcial":
            asset_classification = "Dados parciais"
            asset_term = "Aguardando dados"
            d_reasons = [
                "Dados de proventos ainda estao parciais para este ativo.",
                "A leitura sera recalculada quando a fonte externa trouxer historico, payout e consistencia.",
            ]
            g_reasons = [
                "Dados de crescimento ainda estao parciais para este ativo.",
                "Receita, lucro, margens e retorno sobre capital precisam ser complementados pela fonte externa.",
            ]
        rows.append(
            {
                "assetId": asset.id,
                "ticker": asset.ticker,
                "name": asset.name,
                "class": asset.asset_class,
                "sector": asset.sector,
                "price": float(asset.snapshot.price),
                "dividendYield": float(asset.snapshot.dividend_yield),
                "scoreDividendos": d_score,
                "scoreCrescimento": g_score,
                "scoreSeguranca": sec_score,
                "scoreValuation": val_score,
                "scoreRisco": r_score,
                "scoreFinal": final_score,
                "classification": asset_classification,
                "term": asset_term,
                "dataStatus": data_status,
                "dataFields": filled_fields,
                "dividendJustification": " ".join(d_reasons),
                "growthJustification": " ".join(g_reasons),
                "finalJustification": (
                    "Dados parciais: o score e apenas uma leitura provisoria ate a fonte externa completar os fundamentos."
                    if data_status == "parcial"
                    else "Score final combina proventos, crescimento, seguranca, valuation e risco. "
                    "A leitura e analitica e nao representa recomendacao de compra ou venda."
                ),
            }
        )
    return sorted(rows, key=lambda item: item["scoreFinal"], reverse=True)
