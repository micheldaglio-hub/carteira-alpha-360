from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TargetAllocation
from app.services.portfolio import get_allocations, get_positions


def get_rebalance_plan(db: Session, user_id: str, next_contribution: float = 2500) -> dict:
    positions = get_positions(db, user_id)
    allocations = get_allocations(positions)
    current_by_asset = {item["name"]: item["weight"] for item in allocations["byAsset"]}

    targets = (
        db.execute(select(TargetAllocation).where(TargetAllocation.user_id == user_id, TargetAllocation.level == "asset"))
        .scalars()
        .all()
    )
    if not targets:
        total_assets = len(current_by_asset) or 1
        targets_map = {ticker: round(100 / total_assets, 2) for ticker in current_by_asset}
        profile = "equilibrado"
    else:
        targets_map = {target.target_key: float(target.percentage) for target in targets}
        profile = targets[0].profile

    rows = []
    deficits = []
    for ticker, ideal in targets_map.items():
        current = current_by_asset.get(ticker, 0)
        diff = round(ideal - current, 2)
        status = "abaixo_do_peso" if diff > 1 else "acima_do_peso" if diff < -1 else "alinhado"
        if diff > 0:
            deficits.append((ticker, diff))
        rows.append({"ticker": ticker, "current": round(current, 2), "ideal": round(ideal, 2), "difference": diff, "status": status})

    deficit_sum = sum(diff for _, diff in deficits)
    suggestions = [
        {
            "ticker": ticker,
            "suggestedAmount": round(next_contribution * diff / deficit_sum, 2) if deficit_sum else 0,
            "reason": "Abaixo da alocacao ideal definida para o perfil.",
        }
        for ticker, diff in deficits
    ]

    overweight = [row for row in rows if row["status"] == "acima_do_peso"]
    underweight = [row for row in rows if row["status"] == "abaixo_do_peso"]
    concentration = [position for position in positions if position["weight"] >= 20]
    concentration_risk = "alto" if concentration else "controlado"

    return {
        "profile": profile,
        "nextContribution": next_contribution,
        "currentAllocation": allocations,
        "targets": sorted(rows, key=lambda item: item["difference"]),
        "suggestions": suggestions,
        "overweight": overweight,
        "underweight": underweight,
        "concentrationRisk": concentration_risk,
        "concentrationNotes": [
            f"{position['ticker']} representa {position['weight']:.2f}% da carteira."
            for position in concentration
        ],
    }
