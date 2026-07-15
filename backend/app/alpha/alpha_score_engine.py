from __future__ import annotations

from sqlalchemy.orm import Session

from app.alpha.contracts import AlphaScoreV2, ScoreBreakdown
from app.alpha.utils import band, clamp, inverse_band, percent
from app.models import Asset
from app.services.portfolio import get_allocations, get_positions
from app.services.scoring import (
    classification,
    dividend_score,
    growth_score,
    market_term,
    risk_score,
    safety_score,
    valuation_score,
)


CLASS_LIQUIDITY = {
    "Acoes": 84,
    "ETFs": 88,
    "FIIs": 72,
    "Renda fixa": 80,
    "Cripto": 62,
}


def _component(nome: str, nota: float, justificativa: str) -> ScoreBreakdown:
    return ScoreBreakdown(nome=nome, nota=round(clamp(nota), 2), justificativa=justificativa)


def _sector_weight(allocations: dict, sector: str) -> float:
    for row in allocations["bySector"]:
        if row["name"] == sector:
            return row["weight"]
    return 0.0


def calculate_alpha_scores_v2(db: Session, user_id: str) -> list[AlphaScoreV2]:
    positions = get_positions(db, user_id)
    allocations = get_allocations(positions)
    rows: list[AlphaScoreV2] = []

    for position in positions:
        asset = db.get(Asset, position["assetId"])
        if asset is None or asset.snapshot is None:
            continue
        snapshot = asset.snapshot
        div_score, div_reasons = dividend_score(snapshot)
        gro_score, gro_reasons = growth_score(snapshot)
        sec_score = safety_score(snapshot)
        val_score = valuation_score(snapshot)
        raw_risk = risk_score(snapshot)
        liquidity = CLASS_LIQUIDITY.get(asset.asset_class, 62)
        concentration = inverse_band(position["weight"], 8, 32)
        sector_weight = _sector_weight(allocations, asset.sector)
        diversification = 100 - max(0, sector_weight - 30) * 1.5 - max(0, position["weight"] - 15) * 1.2
        volatility = 100 - raw_risk
        governance = (
            float(snapshot.recurring_profit or 0) * 0.32
            + float(snapshot.sector_stability or 0) * 0.25
            + inverse_band(float(snapshot.debt_to_ebitda or 0), 0, 5) * 0.25
            + float(snapshot.dividend_consistency or 0) * 0.18
        )
        result = (
            band(float(snapshot.revenue_growth or 0), -5, 25) * 0.22
            + band(float(snapshot.profit_growth or 0), -8, 30) * 0.26
            + band(float(snapshot.net_margin or 0), 5, 35) * 0.18
            + band(float(snapshot.roe or 0), 5, 28) * 0.17
            + band(float(snapshot.roic or 0), 4, 24) * 0.17
        )
        final = (
            div_score * 0.16
            + gro_score * 0.16
            + sec_score * 0.13
            + val_score * 0.11
            + liquidity * 0.08
            + concentration * 0.10
            + diversification * 0.08
            + volatility * 0.07
            + governance * 0.05
            + result * 0.06
        )
        final = round(clamp(final), 2)
        rows.append(
            AlphaScoreV2(
                assetId=asset.id,
                ticker=asset.ticker,
                nome=asset.name,
                classe=asset.asset_class,
                setor=asset.sector,
                termo=market_term(final, val_score, div_score, gro_score),
                classificacao=classification(final),
                scoreFinal=final,
                justificativaFinal=(
                    "Score final combina proventos, crescimento, seguranca, valuation, liquidez, "
                    "concentracao, diversificacao, volatilidade, governanca e resultado. "
                    "A leitura e analitica e nao representa recomendacao de compra ou venda."
                ),
                scores=[
                    _component("Proventos", div_score, " ".join(div_reasons)),
                    _component("Crescimento", gro_score, " ".join(gro_reasons)),
                    _component("Seguranca", sec_score, "Alavancagem, recorrencia de lucro e estabilidade setorial."),
                    _component("Valuation", val_score, "Leitura relativa de multiplos e faixa de valor historica."),
                    _component("Liquidez", liquidity, f"Classe {asset.asset_class} recebeu nota de liquidez operacional."),
                    _component("Concentracao", concentration, f"{asset.ticker} representa {percent(position['weight'])} da carteira."),
                    _component("Diversificacao", diversification, f"O setor {asset.sector} representa {percent(sector_weight)} da carteira."),
                    _component("Volatilidade", volatility, "Nota inversa ao risco fundamental estimado do ativo."),
                    _component("Governanca", governance, "Proxy baseada em recorrencia, estabilidade e alavancagem."),
                    _component("Resultado", result, "Receita, lucro, margens, ROE e ROIC compoem esta leitura."),
                ],
            )
        )

    return sorted(rows, key=lambda item: item.scoreFinal, reverse=True)
