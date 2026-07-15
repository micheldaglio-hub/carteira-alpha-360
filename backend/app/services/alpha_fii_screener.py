from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.asset_engine import ensure_asset_engine_metadata
from app.models import Asset
from app.services.market_data.sync import sync_asset_market_data


FII_CANDIDATES = [
    {
        "ticker": "HGLG11",
        "name": "CSHG Logistica",
        "segment": "Logistica",
        "incomeConsistency": 90,
        "liquidity": 90,
        "portfolioQuality": 88,
        "management": 88,
        "valuationDiscipline": 76,
        "risk": 30,
        "role": "Nucleo logistico",
        "thesis": "FII logistico de alta qualidade, com imoveis relevantes, boa liquidez e historico consistente de rendimentos.",
        "watchpoints": ["Vacancia", "Revisao de aluguel", "Preco sobre valor patrimonial"],
    },
    {
        "ticker": "KNRI11",
        "name": "Kinea Renda Imobiliaria",
        "segment": "Hibrido",
        "incomeConsistency": 88,
        "liquidity": 88,
        "portfolioQuality": 86,
        "management": 90,
        "valuationDiscipline": 78,
        "risk": 32,
        "role": "Diversificacao imobiliaria",
        "thesis": "FII hibrido com carteira diversificada, gestao reconhecida e papel defensivo em renda imobiliaria.",
        "watchpoints": ["Exposicao a escritorios", "Vacancia", "Renovacao de contratos"],
    },
    {
        "ticker": "BTLG11",
        "name": "BTG Pactual Logistica",
        "segment": "Logistica",
        "incomeConsistency": 86,
        "liquidity": 86,
        "portfolioQuality": 86,
        "management": 86,
        "valuationDiscipline": 76,
        "risk": 34,
        "role": "Logistica complementar",
        "thesis": "FII logistico com boa escala, ativos de qualidade e perfil adequado para renda recorrente.",
        "watchpoints": ["Concentracao de inquilinos", "Cap rate", "Alavancagem"],
    },
    {
        "ticker": "XPML11",
        "name": "XP Malls",
        "segment": "Shoppings",
        "incomeConsistency": 84,
        "liquidity": 90,
        "portfolioQuality": 84,
        "management": 84,
        "valuationDiscipline": 74,
        "risk": 38,
        "role": "Consumo e shoppings",
        "thesis": "FII de shoppings com escala, liquidez e potencial de renda ligada ao consumo.",
        "watchpoints": ["Ciclo de consumo", "Juros altos", "Vacancia e inadimplencia"],
    },
    {
        "ticker": "VISC11",
        "name": "Vinci Shopping Centers",
        "segment": "Shoppings",
        "incomeConsistency": 82,
        "liquidity": 84,
        "portfolioQuality": 82,
        "management": 84,
        "valuationDiscipline": 76,
        "risk": 40,
        "role": "Shoppings diversificados",
        "thesis": "FII de shoppings com diversificacao e historico relevante para renda imobiliaria.",
        "watchpoints": ["Ciclo de varejo", "Vacancia", "Juros"],
    },
    {
        "ticker": "KNCR11",
        "name": "Kinea Rendimentos Imobiliarios",
        "segment": "Recebiveis",
        "incomeConsistency": 86,
        "liquidity": 88,
        "portfolioQuality": 80,
        "management": 90,
        "valuationDiscipline": 72,
        "risk": 38,
        "role": "Renda indexada",
        "thesis": "FII de recebiveis com gestao forte e perfil de renda mais ligado a juros e inflacao.",
        "watchpoints": ["Qualidade dos CRIs", "Indexadores", "Risco de credito"],
    },
    {
        "ticker": "MXRF11",
        "name": "Maxi Renda",
        "segment": "Recebiveis",
        "incomeConsistency": 82,
        "liquidity": 92,
        "portfolioQuality": 72,
        "management": 76,
        "valuationDiscipline": 70,
        "risk": 45,
        "role": "Renda mensal com peso controlado",
        "thesis": "FII popular e liquido, com renda recorrente, mas que exige peso controlado por qualidade e risco de credito.",
        "watchpoints": ["Qualidade da carteira", "Risco de credito", "Diluição em emissoes"],
    },
    {
        "ticker": "CPTS11",
        "name": "Capitania Securities II",
        "segment": "Recebiveis",
        "incomeConsistency": 78,
        "liquidity": 78,
        "portfolioQuality": 74,
        "management": 78,
        "valuationDiscipline": 74,
        "risk": 48,
        "role": "Recebiveis com risco controlado",
        "thesis": "FII de recebiveis para complementar renda, desde que acompanhado por risco de credito e qualidade dos CRIs.",
        "watchpoints": ["Credito privado", "Indexadores", "Volatilidade das cotas"],
    },
]

FII_TARGET_WEIGHTS = {
    "HGLG11": 16,
    "KNRI11": 15,
    "BTLG11": 14,
    "XPML11": 13,
    "VISC11": 11,
    "KNCR11": 12,
    "MXRF11": 10,
    "CPTS11": 9,
}


def run_alpha_fii_screener(db: Session | None = None, *, refresh_market: bool = False) -> dict:
    rows = []
    for candidate in FII_CANDIDATES:
        asset = _ensure_fii_asset(db, candidate) if db is not None else None
        if db is not None and asset is not None and refresh_market:
            try:
                sync_asset_market_data(db, asset)
            except Exception:
                pass
        rows.append(_score_candidate(candidate))

    ranking = sorted(rows, key=lambda item: item["alphaScore"], reverse=True)
    by_ticker = {row["ticker"]: row for row in ranking}
    portfolio = []
    for ticker, weight in FII_TARGET_WEIGHTS.items():
        row = by_ticker[ticker]
        portfolio.append({**row, "targetWeight": weight, "class": "FIIs"})

    segment_allocation: dict[str, float] = {}
    for item in portfolio:
        segment_allocation[item["segment"]] = segment_allocation.get(item["segment"], 0) + float(item["targetWeight"])

    if db is not None and refresh_market:
        db.commit()

    return {
        "id": "screener-alpha-fiis-proventos-2026-07-12",
        "title": "Screener Alpha FIIs",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "foundation_ready",
        "strategy": "Renda imobiliaria, recorrencia de proventos, qualidade dos ativos, liquidez e risco controlado.",
        "selectedCount": len(portfolio),
        "candidateCount": len(rows),
        "filters": [
            "Tratar FII como ativo de renda imobiliaria, nao como empresa operacional.",
            "Priorizar recorrencia de rendimentos, qualidade dos imoveis, liquidez, gestao e diversificacao.",
            "Separar segmentos: logistica, hibrido, shoppings e recebiveis.",
            "Acompanhar P/VP, vacancia, inadimplencia, emissões, qualidade dos CRIs e concentracao de inquilinos.",
            "Validar isencao de IR conforme regras vigentes antes de qualquer planejamento tributario.",
        ],
        "portfolio": portfolio,
        "ranking": ranking,
        "segmentAllocation": [{"name": name, "value": value} for name, value in sorted(segment_allocation.items())],
        "taxNote": "Rendimentos de FIIs podem ser isentos para pessoa fisica quando atendem aos requisitos legais. Ganho de capital na venda de cotas nao segue a mesma logica.",
        "dataNote": "Nesta fase o motor usa conhecimento estrutural e fica preparado para receber dados reais de B3, Fintz, CVM, Dados de Mercado ou outro provider.",
    }


def _score_candidate(candidate: dict) -> dict:
    score = (
        candidate["incomeConsistency"] * 0.24
        + candidate["liquidity"] * 0.16
        + candidate["portfolioQuality"] * 0.22
        + candidate["management"] * 0.16
        + candidate["valuationDiscipline"] * 0.12
        + (100 - candidate["risk"]) * 0.10
    )
    alpha_score = round(max(0, min(100, score)), 2)
    if alpha_score >= 86:
        reading = "Nucleo imobiliario"
    elif alpha_score >= 80:
        reading = "Alta qualidade"
    elif alpha_score >= 74:
        reading = "Compoe renda imobiliaria"
    else:
        reading = "Peso controlado"
    return {
        "ticker": candidate["ticker"],
        "name": candidate["name"],
        "segment": candidate["segment"],
        "role": candidate["role"],
        "alphaScore": alpha_score,
        "alphaReading": f"{reading}: {candidate['ticker']} entra pela combinacao de renda recorrente, qualidade do portfolio e liquidez relativa.",
        "riskLevel": "baixo_moderado" if alpha_score >= 82 else "moderado" if alpha_score >= 76 else "controlado",
        "scores": {
            "incomeConsistency": candidate["incomeConsistency"],
            "liquidity": candidate["liquidity"],
            "portfolioQuality": candidate["portfolioQuality"],
            "management": candidate["management"],
            "valuationDiscipline": candidate["valuationDiscipline"],
            "risk": candidate["risk"],
        },
        "thesis": candidate["thesis"],
        "watchpoints": candidate["watchpoints"],
        "whySelected": [
            f"Segmento {candidate['segment']} adiciona exposicao imobiliaria com perfil de renda.",
            candidate["thesis"],
            "Rendimentos mensais devem ser tratados como proventos, separados de ganho de capital da cota.",
        ],
    }


def _ensure_fii_asset(db: Session | None, candidate: dict) -> Asset | None:
    if db is None:
        return None
    asset = db.execute(select(Asset).where(Asset.ticker == candidate["ticker"])).scalar_one_or_none()
    if asset is not None:
        return asset
    asset = Asset(
        ticker=candidate["ticker"],
        name=candidate["name"],
        asset_class="FIIs",
        sector="Fundos imobiliarios",
        segment=candidate["segment"],
        currency="BRL",
        provider_symbol=candidate["ticker"],
        last_price=Decimal("0"),
    )
    ensure_asset_engine_metadata(db, asset, force=True)
    db.add(asset)
    db.flush()
    return asset
