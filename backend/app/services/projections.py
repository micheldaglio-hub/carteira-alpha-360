from __future__ import annotations

from app.engines.financial_projection_engine import FinancialProjectionEngine
from app.schemas import ProjectionRequest


def simulate_projection(payload: ProjectionRequest, *, current_wealth_for_goal: float | None = None) -> dict:
    return FinancialProjectionEngine().simulate(payload, current_wealth_for_goal=current_wealth_for_goal)
