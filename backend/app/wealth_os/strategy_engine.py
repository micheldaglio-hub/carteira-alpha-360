from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset
from app.services.asset_taxonomy import classify_position
from app.services.portfolio import get_allocations, get_dashboard, get_positions
from app.wealth_os.contracts import (
    StrategyAssessment,
    StrategyAssetFit,
    StrategyDefinition,
    StrategyEngineReport,
    StrategyFactorResult,
    clamp,
)
from app.wealth_os.utils import as_float, status_from_score


@dataclass(frozen=True)
class StrategyConfig:
    id: str
    name: str
    archetype: str
    description: str
    risk_profile: str
    time_horizon: str
    philosophy: tuple[str, ...]
    target_allocation: dict[str, float]
    factor_weights: dict[str, float]
    preferred_sectors: tuple[str, ...] = ()
    preferred_classes: tuple[str, ...] = ()
    max_crypto: float = 10
    max_asset: float = 18
    max_sector: float = 40
    income_target_yield: float = 6
    global_target: float = 10


STRATEGIES: tuple[StrategyConfig, ...] = (
    StrategyConfig(
        id="dividendos",
        name="Dividendos",
        archetype="Renda passiva",
        description="Busca renda distribuida recorrente, previsibilidade de caixa e setores essenciais.",
        risk_profile="moderado",
        time_horizon="longo prazo",
        philosophy=("Priorizar proventos sustentaveis.", "Evitar concentracao excessiva.", "Separar dividendo alto de dividendo saudavel."),
        target_allocation={"Acoes Brasil": 55, "FIIs": 25, "ETFs": 8, "Global": 7, "Cripto": 5, "Caixa/Renda Fixa": 0},
        factor_weights={"allocation": 0.22, "income": 0.28, "concentration": 0.18, "diversification": 0.14, "global": 0.06, "crypto": 0.06, "quality": 0.06},
        preferred_sectors=("Energia", "Bancos", "Seguros", "Saneamento", "Telecom", "Holding financeira", "Fundos imobiliarios"),
        preferred_classes=("Acoes Brasil", "FIIs"),
        max_crypto=8,
        max_asset=16,
        max_sector=42,
        income_target_yield=7,
        global_target=7,
    ),
    StrategyConfig(
        id="crescimento",
        name="Crescimento",
        archetype="Expansao patrimonial",
        description="Aceita mais volatilidade para buscar empresas com reinvestimento, tecnologia, escala e crescimento de lucro.",
        risk_profile="moderado_arrojado",
        time_horizon="longo prazo",
        philosophy=("Crescimento precisa de caixa, margem e vantagem competitiva.", "Valuation importa mesmo em empresas excelentes.", "Volatilidade nao deve virar ausencia de controle."),
        target_allocation={"Acoes Brasil": 42, "FIIs": 5, "ETFs": 12, "Global": 28, "Cripto": 10, "Caixa/Renda Fixa": 3},
        factor_weights={"allocation": 0.2, "income": 0.04, "concentration": 0.14, "diversification": 0.13, "global": 0.2, "crypto": 0.08, "quality": 0.21},
        preferred_sectors=("Tecnologia", "Semicondutores", "Pagamentos", "Saude", "Industria", "Bens industriais", "Consumo"),
        preferred_classes=("Acoes Brasil", "Global", "ETFs"),
        max_crypto=12,
        max_asset=18,
        max_sector=38,
        income_target_yield=2,
        global_target=28,
    ),
    StrategyConfig(
        id="global",
        name="Global",
        archetype="Diversificacao internacional",
        description="Reduz dependencia de Brasil e BRL com empresas, ETFs e moedas internacionais.",
        risk_profile="moderado",
        time_horizon="longo prazo",
        philosophy=("Patrimonio global nao depende de uma unica moeda.", "Comparar stock, BDR e ETF antes de executar.", "Diversificar pais, moeda, setor e bolsa."),
        target_allocation={"Acoes Brasil": 25, "FIIs": 8, "ETFs": 20, "Global": 40, "Cripto": 5, "Caixa/Renda Fixa": 2},
        factor_weights={"allocation": 0.26, "income": 0.04, "concentration": 0.14, "diversification": 0.16, "global": 0.28, "crypto": 0.05, "quality": 0.07},
        preferred_sectors=("Tecnologia", "Saude", "Pagamentos", "Consumo", "Semicondutores", "ETFs globais"),
        preferred_classes=("Global", "ETFs"),
        max_crypto=8,
        max_asset=14,
        max_sector=35,
        income_target_yield=3,
        global_target=40,
    ),
    StrategyConfig(
        id="cripto_controlado",
        name="Cripto Controlado",
        archetype="Assimetria com limite",
        description="Permite opcionalidade em cripto, mas com teto de risco e separacao do nucleo patrimonial.",
        risk_profile="arrojado_controlado",
        time_horizon="longo prazo",
        philosophy=("Cripto e opcionalidade, nao base da aposentadoria.", "Limite de peso protege o plano principal.", "Pesquisa e liquidez importam mais que narrativa."),
        target_allocation={"Acoes Brasil": 45, "FIIs": 15, "ETFs": 10, "Global": 20, "Cripto": 8, "Caixa/Renda Fixa": 2},
        factor_weights={"allocation": 0.18, "income": 0.08, "concentration": 0.2, "diversification": 0.14, "global": 0.12, "crypto": 0.22, "quality": 0.06},
        preferred_sectors=("Cripto", "Tecnologia", "Pagamentos", "Energia", "Bancos"),
        preferred_classes=("Cripto", "Global", "Acoes Brasil"),
        max_crypto=10,
        max_asset=16,
        max_sector=40,
        income_target_yield=4,
        global_target=20,
    ),
    StrategyConfig(
        id="aposentadoria",
        name="Aposentadoria",
        archetype="Independencia financeira",
        description="Equilibra renda passiva, preservacao, diversificacao e previsibilidade de longo prazo.",
        risk_profile="moderado_conservador",
        time_horizon="muito longo prazo",
        philosophy=("A renda passiva deve ser sustentavel.", "Evitar apostas que ameacem o plano.", "Inflacao, imposto e cambio precisam entrar na leitura."),
        target_allocation={"Acoes Brasil": 45, "FIIs": 22, "ETFs": 13, "Global": 15, "Cripto": 3, "Caixa/Renda Fixa": 2},
        factor_weights={"allocation": 0.22, "income": 0.25, "concentration": 0.2, "diversification": 0.16, "global": 0.08, "crypto": 0.05, "quality": 0.04},
        preferred_sectors=("Energia", "Saneamento", "Bancos", "Seguros", "Telecom", "Fundos imobiliarios"),
        preferred_classes=("Acoes Brasil", "FIIs", "ETFs", "Global"),
        max_crypto=5,
        max_asset=14,
        max_sector=35,
        income_target_yield=6.5,
        global_target=15,
    ),
    StrategyConfig(
        id="barsi",
        name="Barsi",
        archetype="Dividendos perenes Brasil",
        description="Inspirado em acumulacao de empresas brasileiras lucrativas, perenes e pagadoras de proventos.",
        risk_profile="moderado",
        time_horizon="muito longo prazo",
        philosophy=("Comprar negocios, nao tickers.", "Proventos recorrentes aceleram acumulacao.", "Setores essenciais reduzem risco de tese fraca."),
        target_allocation={"Acoes Brasil": 70, "FIIs": 15, "ETFs": 5, "Global": 5, "Cripto": 3, "Caixa/Renda Fixa": 2},
        factor_weights={"allocation": 0.24, "income": 0.28, "concentration": 0.16, "diversification": 0.12, "global": 0.04, "crypto": 0.06, "quality": 0.1},
        preferred_sectors=("Energia", "Bancos", "Seguros", "Saneamento", "Telecom", "Holding financeira"),
        preferred_classes=("Acoes Brasil", "FIIs"),
        max_crypto=5,
        max_asset=18,
        max_sector=45,
        income_target_yield=7,
        global_target=5,
    ),
    StrategyConfig(
        id="buffett",
        name="Buffett",
        archetype="Quality + Value",
        description="Busca negocios excelentes, vantagem competitiva, caixa e paciencia para longo prazo.",
        risk_profile="moderado",
        time_horizon="muito longo prazo",
        philosophy=("Qualidade vem antes de pressa.", "Preco importa.", "Negocios simples e duraveis valem mais que modismos."),
        target_allocation={"Acoes Brasil": 45, "FIIs": 5, "ETFs": 5, "Global": 40, "Cripto": 2, "Caixa/Renda Fixa": 3},
        factor_weights={"allocation": 0.2, "income": 0.08, "concentration": 0.16, "diversification": 0.1, "global": 0.22, "crypto": 0.08, "quality": 0.16},
        preferred_sectors=("Bancos", "Seguros", "Pagamentos", "Consumo", "Saude", "Tecnologia", "Energia"),
        preferred_classes=("Acoes Brasil", "Global"),
        max_crypto=4,
        max_asset=20,
        max_sector=35,
        income_target_yield=3.5,
        global_target=40,
    ),
    StrategyConfig(
        id="bogle",
        name="Bogle",
        archetype="ETFs globais",
        description="Foco em simplicidade, baixo giro, ETFs amplos, diversificacao global e disciplina.",
        risk_profile="moderado",
        time_horizon="muito longo prazo",
        philosophy=("Simplicidade vence excesso de decisao.", "Baixo custo e diversificacao ampla.", "Evitar tentar acertar o ativo perfeito todo mes."),
        target_allocation={"Acoes Brasil": 10, "FIIs": 5, "ETFs": 45, "Global": 35, "Cripto": 3, "Caixa/Renda Fixa": 2},
        factor_weights={"allocation": 0.32, "income": 0.03, "concentration": 0.16, "diversification": 0.2, "global": 0.2, "crypto": 0.05, "quality": 0.04},
        preferred_sectors=("ETFs globais", "Brasil amplo", "Exterior", "Indice"),
        preferred_classes=("ETFs", "Global"),
        max_crypto=5,
        max_asset=12,
        max_sector=30,
        income_target_yield=2,
        global_target=35,
    ),
    StrategyConfig(
        id="dalio",
        name="Dalio",
        archetype="All Weather",
        description="Busca equilibrio entre crescimento, renda, moeda, protecao e descorrelacao.",
        risk_profile="moderado_conservador",
        time_horizon="longo prazo",
        philosophy=("Cenarios diferentes pedem ativos diferentes.", "Descorrelacao reduz dependencia de previsao.", "Caixa, renda fixa, ouro e global entram no desenho futuro."),
        target_allocation={"Acoes Brasil": 25, "FIIs": 10, "ETFs": 25, "Global": 25, "Cripto": 3, "Caixa/Renda Fixa": 12},
        factor_weights={"allocation": 0.3, "income": 0.08, "concentration": 0.2, "diversification": 0.2, "global": 0.12, "crypto": 0.05, "quality": 0.05},
        preferred_sectors=("ETFs globais", "Renda fixa", "Ouro", "Energia", "Saude"),
        preferred_classes=("ETFs", "Global", "Caixa/Renda Fixa", "FIIs"),
        max_crypto=5,
        max_asset=12,
        max_sector=28,
        income_target_yield=3.5,
        global_target=25,
    ),
    StrategyConfig(
        id="lynch",
        name="Lynch",
        archetype="Crescimento compreensivel",
        description="Busca empresas compreensiveis, crescimento operacional e assimetria sem abandonar fundamentos.",
        risk_profile="moderado_arrojado",
        time_horizon="longo prazo",
        philosophy=("Entender o negocio antes da tese.", "Crescimento precisa aparecer em resultados.", "Assimetria nao dispensa diversificacao."),
        target_allocation={"Acoes Brasil": 50, "FIIs": 5, "ETFs": 10, "Global": 25, "Cripto": 8, "Caixa/Renda Fixa": 2},
        factor_weights={"allocation": 0.2, "income": 0.04, "concentration": 0.14, "diversification": 0.16, "global": 0.16, "crypto": 0.08, "quality": 0.22},
        preferred_sectors=("Tecnologia", "Consumo", "Industria", "Saude", "Bens industriais", "Pagamentos"),
        preferred_classes=("Acoes Brasil", "Global", "Cripto"),
        max_crypto=10,
        max_asset=16,
        max_sector=38,
        income_target_yield=2,
        global_target=25,
    ),
)


def build_strategy_report(db: Session, user_id: str) -> StrategyEngineReport:
    positions = get_positions(db, user_id)
    dashboard = get_dashboard(db, user_id)
    allocations = (dashboard.get("portfolioSnapshot") or {}).get("allocations") or get_allocations(positions)
    asset_meta = _load_asset_meta(db, positions)
    current_allocation = _allocation_by_bucket(positions, asset_meta, dashboard)
    metrics = _strategy_metrics(positions, dashboard, allocations, asset_meta, current_allocation)
    assessments = [_assess_strategy(config, positions, asset_meta, current_allocation, metrics) for config in STRATEGIES]
    assessments = sorted(assessments, key=lambda item: item.score, reverse=True)
    primary = assessments[0] if assessments else None
    headline = "Strategy Engine 2.0 classificou a carteira contra perfis patrimoniais."
    if primary:
        headline = f"A carteira hoje combina mais com {primary.strategy.name}, com aderencia de {primary.score:.0f}/100."

    return StrategyEngineReport(
        status="operacional",
        headline=headline,
        primaryStrategy=primary.strategy.id if primary else "",
        primaryScore=round(primary.score, 2) if primary else 0,
        currentAllocation=current_allocation,
        metrics=metrics,
        assessments=assessments,
        rules=[
            "A leitura mede compatibilidade estrategica, nao ordem automatica de compra ou venda.",
            "Perfis podem coexistir: a carteira pode ser de dividendos com satelite global e cripto controlado.",
            "Desalinhamento deve orientar estudos e proximos aportes, nao decisao impulsiva.",
            "Estrategias inspiradas em investidores famosos sao traducoes conceituais, nao copias exatas de carteiras reais.",
        ],
        updatedAt=datetime.now(timezone.utc).isoformat(),
    )


def _load_asset_meta(db: Session, positions: list[dict]) -> dict[str, Asset]:
    ids = [item.get("assetId") for item in positions if item.get("assetId")]
    if not ids:
        return {}
    assets = db.execute(select(Asset).where(Asset.id.in_(ids))).scalars().all()
    return {asset.id: asset for asset in assets}


def _allocation_by_bucket(positions: list[dict], asset_meta: dict[str, Asset], dashboard: dict | None = None) -> dict[str, float]:
    totals = {bucket: 0.0 for bucket in ["Acoes Brasil", "FIIs", "ETFs", "Global", "Cripto", "Caixa/Renda Fixa", "Outros"]}
    snapshot_rows = (((dashboard or {}).get("portfolioSnapshot") or {}).get("allocations") or {}).get("byStrategyBucket") or []
    if snapshot_rows:
        for row in snapshot_rows:
            bucket = str(row.get("name") or "Outros")
            if bucket == "Trading":
                totals["Outros"] += as_float(row.get("weight"))
            else:
                totals[bucket] = totals.get(bucket, 0.0) + as_float(row.get("weight"))
        return {key: round(value, 2) for key, value in totals.items() if value > 0 or key != "Outros"}
    total_value = sum(as_float(item.get("currentValue")) for item in positions)
    if total_value <= 0:
        return {key: 0.0 for key in totals}
    for position in positions:
        asset = asset_meta.get(str(position.get("assetId")))
        bucket = _bucket_for(position, asset)
        totals[bucket] = totals.get(bucket, 0.0) + as_float(position.get("currentValue"))
    return {key: round(value / total_value * 100, 2) for key, value in totals.items() if value > 0 or key != "Outros"}


def _strategy_metrics(positions: list[dict], dashboard: dict, allocations: dict, asset_meta: dict[str, Asset], current_allocation: dict[str, float]) -> dict[str, float]:
    metrics = dashboard["metrics"]
    snapshot = dashboard.get("portfolioSnapshot") or {}
    snapshot_exposures = snapshot.get("exposures") or {}
    snapshot_largest = snapshot.get("largest") or {}
    total_equity = as_float(metrics.get("totalEquity"))
    passive_income = as_float(metrics.get("projectedPassiveIncome"))
    income_yield = passive_income * 12 / total_equity * 100 if total_equity else 0
    largest_asset = as_float((snapshot_largest.get("asset") or {}).get("weight")) or max((as_float(item.get("weight")) for item in positions), default=0)
    largest_sector = max((as_float(item.get("weight")) for item in allocations.get("bySector", [])), default=0)
    class_count = len({key for key, value in current_allocation.items() if value > 0})
    sector_count = len({item.get("sector") for item in positions if item.get("sector")})
    preferred_quality = _quality_proxy(positions, asset_meta)
    global_exposure = as_float(snapshot_exposures.get("globalPct"))
    if global_exposure <= 0:
        global_exposure = current_allocation.get("Global", 0.0) + current_allocation.get("ETFs", 0.0) * 0.45
    return {
        "totalEquity": round(total_equity, 2),
        "assetCount": float(len(positions)),
        "classCount": float(class_count),
        "sectorCount": float(sector_count),
        "largestAssetWeight": round(largest_asset, 2),
        "largestSectorWeight": round(largest_sector, 2),
        "cryptoWeight": round(as_float(snapshot_exposures.get("cryptoPct")) or current_allocation.get("Cripto", 0.0), 2),
        "fixedIncomeWeight": round(as_float(snapshot_exposures.get("fixedIncomePct")) or current_allocation.get("Caixa/Renda Fixa", 0.0), 2),
        "globalExposure": round(global_exposure, 2),
        "incomeAnnualYield": round(income_yield, 2),
        "qualityProxy": round(preferred_quality, 2),
        "pnlPct": as_float(metrics.get("pnlPct")),
    }


def _assess_strategy(
    config: StrategyConfig,
    positions: list[dict],
    asset_meta: dict[str, Asset],
    current_allocation: dict[str, float],
    metrics: dict[str, float],
) -> StrategyAssessment:
    factors = [
        _factor("allocation", "Alocacao por classe", _allocation_score(current_allocation, config.target_allocation), "Compara sua alocacao atual com o alvo tecnico do perfil.", config.factor_weights["allocation"]),
        _factor("income", "Renda passiva", _income_score(metrics["incomeAnnualYield"], config.income_target_yield), f"Yield anual estimado de proventos: {metrics['incomeAnnualYield']:.2f}%.", config.factor_weights["income"]),
        _factor("concentration", "Concentracao", _concentration_score(metrics, config), f"Maior ativo {metrics['largestAssetWeight']:.2f}% e maior setor {metrics['largestSectorWeight']:.2f}%.", config.factor_weights["concentration"]),
        _factor("diversification", "Diversificacao", _diversification_score(metrics), f"{int(metrics['assetCount'])} ativos, {int(metrics['classCount'])} classes e {int(metrics['sectorCount'])} setores.", config.factor_weights["diversification"]),
        _factor("global", "Exposicao global", _target_score(metrics["globalExposure"], config.global_target), f"Exposicao global aproximada: {metrics['globalExposure']:.2f}%.", config.factor_weights["global"]),
        _factor("crypto", "Cripto controlado", _crypto_score(metrics["cryptoWeight"], config), f"Cripto em {metrics['cryptoWeight']:.2f}% da carteira.", config.factor_weights["crypto"]),
        _factor("quality", "Qualidade setorial", _sector_fit_score(positions, asset_meta, config), "Mede aderencia dos ativos aos setores/classes preferidos do perfil.", config.factor_weights["quality"]),
    ]
    total_weight = sum(item.weight for item in factors) or 1
    score = sum(item.score * item.weight for item in factors) / total_weight
    normalized = round(clamp(score), 2)
    allocation_gaps = {
        key: round(config.target_allocation.get(key, 0.0) - current_allocation.get(key, 0.0), 2)
        for key in sorted(set(config.target_allocation) | set(current_allocation))
    }
    strengths = [item.reading for item in factors if item.score >= 72][:3]
    attention = [item.reading for item in factors if item.score < 58][:4]
    next_studies = _next_studies(config, allocation_gaps, metrics, factors)
    return StrategyAssessment(
        strategy=_definition(config),
        score=normalized,
        classification=_classification(normalized),
        headline=_strategy_headline(config, normalized),
        factors=factors,
        currentAllocation=current_allocation,
        allocationGaps=allocation_gaps,
        strengths=strengths,
        attentionPoints=attention,
        nextStudies=next_studies,
        assetFits=_asset_fits(positions, asset_meta, config)[:8],
    )


def _definition(config: StrategyConfig) -> StrategyDefinition:
    return StrategyDefinition(
        id=config.id,
        name=config.name,
        archetype=config.archetype,
        description=config.description,
        riskProfile=config.risk_profile,
        timeHorizon=config.time_horizon,
        philosophy=list(config.philosophy),
        targetAllocation=config.target_allocation,
    )


def _factor(factor_id: str, label: str, score: float, reading: str, weight: float) -> StrategyFactorResult:
    normalized = round(clamp(score), 2)
    return StrategyFactorResult(
        id=factor_id,
        label=label,
        score=normalized,
        status=status_from_score(normalized),
        reading=reading,
        weight=round(weight, 4),
    )


def _bucket_for(position: dict, asset: Asset | None) -> str:
    return classify_position(position, asset).strategy_bucket
    raw_class = str(position.get("class") or (asset.asset_class if asset else "") or "").lower()
    subclass = str((asset.asset_subclass if asset else "") or position.get("segment") or "").lower()
    sector = str(position.get("sector") or (asset.sector if asset else "") or "").lower()
    currency = str((asset.trading_currency or asset.base_currency or asset.currency) if asset else "").upper()
    country = str(asset.country_code if asset else "").upper()
    region = str(asset.region if asset else "").lower()
    market = str(asset.market if asset else "").lower()
    if "cripto" in raw_class or "crypto" in raw_class:
        return "Cripto"
    if "renda fixa" in raw_class or raw_class in {"fixed income", "cdb", "rdb", "tesouro"} or "cdi" in sector or "renda fixa" in sector:
        return "Caixa/Renda Fixa"
    if "fii" in raw_class or "reit" in raw_class or ("fund" in subclass and "imobili" in sector):
        return "FIIs"
    if "etf" in raw_class:
        if "exterior" in sector or currency not in {"", "BRL"} or country not in {"", "BR"} or region not in {"", "brasil", "latin america", "america latina"}:
            return "Global"
        return "ETFs"
    if currency not in {"", "BRL"} or country not in {"", "BR"} or region not in {"", "brasil", "brazil", "america latina"} or market in {"nasdaq", "nyse"}:
        return "Global"
    if "acao" in raw_class or "acoes" in raw_class or "açoes" in raw_class or "ações" in raw_class:
        return "Acoes Brasil"
    return "Outros"


def _allocation_score(current: dict[str, float], target: dict[str, float]) -> float:
    keys = set(current) | set(target)
    diff = sum(abs(current.get(key, 0.0) - target.get(key, 0.0)) for key in keys)
    return clamp(100 - diff * 0.75)


def _income_score(current_yield: float, target_yield: float) -> float:
    if target_yield <= 0:
        return 70
    return clamp(current_yield / target_yield * 100)


def _concentration_score(metrics: dict[str, float], config: StrategyConfig) -> float:
    asset_penalty = max(0.0, metrics["largestAssetWeight"] - config.max_asset) * 3.0
    sector_penalty = max(0.0, metrics["largestSectorWeight"] - config.max_sector) * 1.5
    return clamp(100 - asset_penalty - sector_penalty)


def _diversification_score(metrics: dict[str, float]) -> float:
    return clamp(metrics["assetCount"] * 4 + metrics["classCount"] * 15 + metrics["sectorCount"] * 4)


def _target_score(current: float, target: float) -> float:
    if target <= 0:
        return 100 if current <= 2 else clamp(100 - current * 5)
    diff = abs(current - target)
    return clamp(100 - diff * 2.2)


def _crypto_score(current: float, config: StrategyConfig) -> float:
    target = config.target_allocation.get("Cripto", 0.0)
    if current > config.max_crypto:
        return clamp(70 - (current - config.max_crypto) * 6)
    if target <= 0:
        return 100 if current <= 2 else clamp(100 - current * 8)
    return clamp(100 - abs(current - target) * 5)


def _sector_fit_score(positions: list[dict], asset_meta: dict[str, Asset], config: StrategyConfig) -> float:
    if not positions:
        return 0
    weighted = 0.0
    total = 0.0
    for position in positions:
        fit = _asset_fit_score(position, asset_meta.get(str(position.get("assetId"))), config)
        weight = as_float(position.get("currentValue"))
        weighted += fit * weight
        total += weight
    return weighted / total if total else 0


def _quality_proxy(positions: list[dict], asset_meta: dict[str, Asset]) -> float:
    if not positions:
        return 0
    defensive = {"energia", "bancos", "seguros", "saneamento", "telecom", "holding financeira", "fundos imobiliarios", "saude", "pagamentos", "tecnologia"}
    score = 0.0
    total = 0.0
    for position in positions:
        sector = str(position.get("sector") or "").lower()
        value = as_float(position.get("currentValue"))
        score += (82 if sector in defensive else 58) * value
        total += value
    return score / total if total else 0


def _asset_fits(positions: list[dict], asset_meta: dict[str, Asset], config: StrategyConfig) -> list[StrategyAssetFit]:
    rows = []
    for position in positions:
        asset = asset_meta.get(str(position.get("assetId")))
        score = round(_asset_fit_score(position, asset, config), 2)
        rows.append(
            StrategyAssetFit(
                ticker=str(position.get("ticker") or ""),
                name=str(position.get("name") or ""),
                assetClass=_bucket_for(position, asset),
                sector=str(position.get("sector") or ""),
                score=score,
                fit=_classification(score),
                reading=_asset_fit_reading(position, asset, config, score),
            )
        )
    return sorted(rows, key=lambda item: item.score, reverse=True)


def _asset_fit_score(position: dict, asset: Asset | None, config: StrategyConfig) -> float:
    bucket = _bucket_for(position, asset)
    sector = str(position.get("sector") or "").lower()
    preferred_sectors = {item.lower() for item in config.preferred_sectors}
    preferred_classes = set(config.preferred_classes)
    score = 42.0
    if bucket in preferred_classes:
        score += 25
    target_weight = config.target_allocation.get(bucket, 0.0)
    score += min(18, target_weight * 0.35)
    if sector in preferred_sectors:
        score += 20
    if bucket == "Cripto" and as_float(position.get("weight")) > config.max_crypto:
        score -= 24
    if as_float(position.get("weight")) > config.max_asset:
        score -= 18
    return clamp(score)


def _asset_fit_reading(position: dict, asset: Asset | None, config: StrategyConfig, score: float) -> str:
    bucket = _bucket_for(position, asset)
    ticker = position.get("ticker")
    if score >= 75:
        return f"{ticker} combina bem com {config.name} pelo papel de {bucket} e setor informado."
    if score >= 55:
        return f"{ticker} tem compatibilidade parcial com {config.name}; vale acompanhar peso, setor e qualidade dos dados."
    return f"{ticker} pesa pouco na tese de {config.name} ou exige estudo adicional antes de aumentar exposicao."


def _next_studies(config: StrategyConfig, gaps: dict[str, float], metrics: dict[str, float], factors: list[StrategyFactorResult]) -> list[str]:
    studies = []
    positive_gaps = sorted(((key, value) for key, value in gaps.items() if value > 8), key=lambda item: item[1], reverse=True)
    negative_gaps = sorted(((key, value) for key, value in gaps.items() if value < -8), key=lambda item: item[1])
    if positive_gaps:
        key, value = positive_gaps[0]
        studies.append(f"Estudar proximos aportes para aproximar {key} do perfil {config.name}; falta cerca de {value:.1f} p.p. contra o alvo.")
    if negative_gaps:
        key, value = negative_gaps[0]
        studies.append(f"Acompanhar sobrepeso em {key}; esta cerca de {abs(value):.1f} p.p. acima do alvo do perfil.")
    if metrics["largestAssetWeight"] > config.max_asset:
        studies.append("Revisar concentracao do maior ativo antes de aumentar exposicao nele.")
    if metrics["cryptoWeight"] > config.max_crypto:
        studies.append("Revisar limite de cripto para que a assimetria nao ameace o plano principal.")
    if not studies:
        weakest = min(factors, key=lambda item: item.score, default=None)
        if weakest:
            studies.append(f"Melhorar o fator '{weakest.label}' para aumentar aderencia ao perfil {config.name}.")
    return studies[:4]


def _strategy_headline(config: StrategyConfig, score: float) -> str:
    if score >= 76:
        return f"A carteira esta bem alinhada ao perfil {config.name}."
    if score >= 58:
        return f"A carteira tem aderencia parcial ao perfil {config.name}."
    return f"A carteira ainda esta distante do perfil {config.name}."


def _classification(score: float) -> str:
    if score >= 78:
        return "Muito alinhada"
    if score >= 64:
        return "Alinhada"
    if score >= 48:
        return "Parcial"
    return "Desalinhada"
