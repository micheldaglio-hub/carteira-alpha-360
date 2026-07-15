from __future__ import annotations

from sqlalchemy.orm import Session

from app.wealth_os.contracts import EconomicReading
from app.wealth_os.macro_fx_engine import build_macro_fx_snapshot


def build_economic_readings(db: Session, user_id: str) -> list[EconomicReading]:
    snapshot = build_macro_fx_snapshot(db, user_id)
    confidence = "alta" if snapshot.status == "real_time" else "media_com_cache_ou_dados_parciais"

    return [
        EconomicReading(
            id=item.id,
            title=item.title,
            status=item.severity,
            reading=item.reading,
            portfolioImpact=item.portfolioImpact,
            dataSources=item.dataUsed,
            confidence=confidence,
        )
        for item in snapshot.portfolioReadings
    ]
