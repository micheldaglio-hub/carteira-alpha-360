from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset
from app.services.asset_taxonomy import classify_position
from app.services.portfolio import get_dashboard, get_positions
from app.wealth_os.contracts import ScenarioResult, StressTestReport
from app.wealth_os.macro_fx_engine import build_macro_fx_snapshot
from app.wealth_os.utils import as_float


@dataclass(frozen=True)
class StressScenario:
    id: str
    title: str
    category: str
    description: str
    shocks: dict[str, float]
    passive_income_shock: float
    assumptions: tuple[str, ...]


SCENARIOS: tuple[StressScenario, ...] = (
    StressScenario(
        id="black_swan_global",
        title="Crise global combinada",
        category="crise",
        description="Simula evento severo com bolsa caindo, FIIs pressionados, cripto despencando, cambio estressado e renda passiva cortada.",
        shocks={"Acoes Brasil": -40, "FIIs": -30, "ETFs Brasil": -25, "Acoes Internacionais": -12, "ETFs Internacionais": -10, "REITs": -20, "Renda Fixa Brasil": 0, "Caixa": 0, "Cripto": -75, "Trading": -20, "Commodities": -5, "Outros": -18},
        passive_income_shock=-35,
        assumptions=(
            "Choque extremo e simultaneo, nao previsao.",
            "Dolar alto ajuda parte global em BRL, mas nao elimina perda de ativos de risco.",
            "Proventos podem ser reduzidos por lucro menor, payout menor e custo de capital maior.",
        ),
    ),
    StressScenario(
        id="b3_crash_30",
        title="Bolsa brasileira -30%",
        category="mercado",
        description="Simula queda ampla da bolsa brasileira com aversao a risco local.",
        shocks={"Acoes Brasil": -30, "FIIs": -14, "ETFs Brasil": -22, "Acoes Internacionais": 4, "ETFs Internacionais": 4, "REITs": -3, "Renda Fixa Brasil": 0.4, "Caixa": 0, "Cripto": -18, "Trading": -8, "Commodities": 2, "Outros": -8},
        passive_income_shock=-12,
        assumptions=(
            "Acoes Brasil sofrem choque principal.",
            "Exposicao global pode suavizar impacto em BRL.",
            "Proventos nao caem na mesma velocidade do preco, mas podem sofrer revisao.",
        ),
    ),
    StressScenario(
        id="usd_brl_650",
        title="Dolar alto e real pressionado",
        category="cambio",
        description="Simula USD/BRL em forte alta, com ativos globais ajudando em BRL e ativos locais sofrendo custo/inflacao.",
        shocks={"Acoes Brasil": -8, "FIIs": -6, "ETFs Brasil": 2, "Acoes Internacionais": 22, "ETFs Internacionais": 22, "REITs": 16, "Renda Fixa Brasil": 0.2, "Caixa": 0, "Cripto": 14, "Trading": -4, "Commodities": 10, "Outros": -2},
        passive_income_shock=-4,
        assumptions=(
            "Ativos dolarizados tendem a subir em BRL quando o real desvaloriza.",
            "Empresas locais podem sofrer com inflacao, custo de capital e insumos.",
            "Cambio alto nao e ganho garantido: depende do ativo subjacente.",
        ),
    ),
    StressScenario(
        id="selic_15",
        title="Selic alta por mais tempo",
        category="juros",
        description="Simula Selic em patamar muito alto, pressionando valuation, FIIs e empresas alavancadas.",
        shocks={"Acoes Brasil": -12, "FIIs": -20, "ETFs Brasil": -8, "Acoes Internacionais": -3, "ETFs Internacionais": -2, "REITs": -10, "Renda Fixa Brasil": 1.5, "Caixa": 0.8, "Cripto": -18, "Trading": -5, "Commodities": 1, "Outros": 0},
        passive_income_shock=-8,
        assumptions=(
            "Juros altos elevam custo de capital e reduzem valor presente dos fluxos.",
            "FIIs tendem a sofrer mais por competicao com renda fixa e custo de financiamento.",
            "Bancos e seguradoras podem ter efeitos mistos; o motor usa choque agregado conservador.",
        ),
    ),
    StressScenario(
        id="crypto_winter_70",
        title="Cripto despenca 70%",
        category="cripto",
        description="Simula inverno cripto severo com perda de liquidez, narrativa fraca e queda forte dos ativos digitais.",
        shocks={"Acoes Brasil": -3, "FIIs": 0, "ETFs Brasil": -2, "Acoes Internacionais": -4, "ETFs Internacionais": -4, "REITs": -5, "Renda Fixa Brasil": 0, "Caixa": 0, "Cripto": -70, "Trading": 0, "Commodities": 0, "Outros": 0},
        passive_income_shock=0,
        assumptions=(
            "Cripto pode cair forte sem aviso e ficar anos lateralizada.",
            "O nucleo de renda passiva nao deve depender de cripto.",
            "Peso pequeno limita dano patrimonial mesmo em queda extrema.",
        ),
    ),
    StressScenario(
        id="passive_income_cut_35",
        title="Renda passiva cai 35%",
        category="renda",
        description="Simula corte relevante de dividendos, JCP e rendimentos de FIIs.",
        shocks={"Acoes Brasil": -10, "FIIs": -12, "ETFs Brasil": -5, "Acoes Internacionais": -3, "ETFs Internacionais": -3, "REITs": -8, "Renda Fixa Brasil": 0, "Caixa": 0, "Cripto": 0, "Trading": 0, "Commodities": 0, "Outros": -2},
        passive_income_shock=-35,
        assumptions=(
            "Renda distribuida pode cair mesmo quando o patrimonio ainda existe.",
            "Cortes podem vir de payout menor, lucro menor, vacancia, credito ou resultado nao recorrente.",
            "Meta de independencia financeira deve usar renda passiva, nao valorizacao patrimonial.",
        ),
    ),
    StressScenario(
        id="inflation_shock",
        title="Inflacao volta forte",
        category="inflacao",
        description="Simula inflacao acelerando, juros pressionados e perda de ganho real.",
        shocks={"Acoes Brasil": -10, "FIIs": -12, "ETFs Brasil": -6, "Acoes Internacionais": 5, "ETFs Internacionais": 5, "REITs": -5, "Renda Fixa Brasil": 0.5, "Caixa": -1, "Cripto": -12, "Trading": -4, "Commodities": 8, "Outros": -4},
        passive_income_shock=-10,
        assumptions=(
            "Inflacao alta reduz poder de compra e pode pressionar margens.",
            "Ativos com contratos reajustaveis tendem a sofrer menos, mas nao ficam imunes.",
            "Dolar e ativos globais podem ajudar parcialmente em BRL.",
        ),
    ),
    StressScenario(
        id="liquidity_freeze",
        title="Liquidez seca no mercado",
        category="liquidez",
        description="Simula spread alto, dificuldade de sair de ativos pequenos e aversao a risco.",
        shocks={"Acoes Brasil": -18, "FIIs": -22, "ETFs Brasil": -10, "Acoes Internacionais": -8, "ETFs Internacionais": -8, "REITs": -16, "Renda Fixa Brasil": -1, "Caixa": 0, "Cripto": -35, "Trading": -12, "Commodities": -6, "Outros": -8},
        passive_income_shock=-15,
        assumptions=(
            "Ativos de menor liquidez podem cair mais que o fundamento no curto prazo.",
            "Caixa e diversificacao reduzem a necessidade de vender no pior momento.",
            "O choque mede fragilidade de carteira, nao probabilidade do evento.",
        ),
    ),
)


def build_scenarios(db: Session, user_id: str) -> list[ScenarioResult]:
    return build_stress_test_report(db, user_id).scenarios


def build_stress_test_report(db: Session, user_id: str) -> StressTestReport:
    dashboard = get_dashboard(db, user_id)
    positions = get_positions(db, user_id)
    assets = _load_asset_meta(db, positions)
    metrics = dashboard["metrics"]
    total = as_float(metrics.get("totalEquity"))
    passive_income = as_float(metrics.get("projectedPassiveIncome"))
    exposures = _build_exposures(positions, assets, dashboard)
    macro_context = _macro_context(db, user_id)
    scenarios = [_apply_scenario(item, exposures, total, passive_income) for item in SCENARIOS]
    scenarios = sorted(scenarios, key=lambda item: item.impactPct)
    worst = scenarios[0] if scenarios else None
    resilience_score = _resilience_score(total, passive_income, exposures, worst)
    risk_level = _risk_level(resilience_score)
    headline = _headline(resilience_score, worst)
    return StressTestReport(
        status="operacional" if total > 0 else "sem_patrimonio",
        headline=headline,
        baseEquity=round(total, 2),
        basePassiveIncome=round(passive_income, 2),
        worstScenarioId=worst.id if worst else "",
        worstImpactValue=round(worst.impactValue, 2) if worst else 0,
        worstImpactPct=round(worst.impactPct, 2) if worst else 0,
        resilienceScore=resilience_score,
        riskLevel=risk_level,
        exposureBreakdown={key: round(value, 2) for key, value in exposures.items()},
        scenarios=scenarios,
        macroContext=macro_context,
        assumptions=[
            "Stress test aplica choques deterministicos sobre a carteira atual; nao e previsao de mercado.",
            "Valores usam posicoes atuais, snapshots disponiveis e integracoes externas quando conectadas.",
            "Renda passiva considera estimativa mensal atual de proventos e pode mudar com novos dados.",
            "Impacto de cambio e macro e aproximado enquanto o Asset Engine nao tiver exposicao multi-moeda completa por ativo.",
        ],
        updatedAt=datetime.now(timezone.utc).isoformat(),
    )


def _load_asset_meta(db: Session, positions: list[dict]) -> dict[str, Asset]:
    ids = [item.get("assetId") for item in positions if item.get("assetId")]
    if not ids:
        return {}
    rows = db.execute(select(Asset).where(Asset.id.in_(ids))).scalars().all()
    return {item.id: item for item in rows}


def _build_exposures(positions: list[dict], assets: dict[str, Asset], dashboard: dict) -> dict[str, float]:
    exposures = {
        "Acoes Brasil": 0.0,
        "FIIs": 0.0,
        "ETFs Brasil": 0.0,
        "Renda Fixa Brasil": 0.0,
        "Caixa": 0.0,
        "Acoes Internacionais": 0.0,
        "ETFs Internacionais": 0.0,
        "REITs": 0.0,
        "Cripto": 0.0,
        "Commodities": 0.0,
        "Trading": as_float(dashboard["metrics"].get("externalEquity")),
        "Outros": 0.0,
    }
    snapshot_rows = (((dashboard or {}).get("portfolioSnapshot") or {}).get("allocations") or {}).get("byClass") or []
    if snapshot_rows:
        exposures["Trading"] = 0.0
        for row in snapshot_rows:
            bucket = str(row.get("name") or "Outros")
            exposures[bucket] = exposures.get(bucket, 0.0) + as_float(row.get("value"))
        return exposures
    for position in positions:
        asset = assets.get(str(position.get("assetId")))
        bucket = _bucket_for(position, asset)
        exposures[bucket] = exposures.get(bucket, 0.0) + as_float(position.get("currentValue"))
    return exposures


def _bucket_for(position: dict, asset: Asset | None) -> str:
    return classify_position(position, asset).asset_class
    raw_class = str(position.get("class") or (asset.asset_class if asset else "") or "").lower()
    sector = str(position.get("sector") or (asset.sector if asset else "") or "").lower()
    currency = str((asset.trading_currency or asset.base_currency or asset.currency) if asset else "").upper()
    country = str(asset.country_code if asset else "").upper()
    region = str(asset.region if asset else "").lower()
    market = str(asset.market if asset else "").lower()
    if "cripto" in raw_class or "crypto" in raw_class:
        return "Cripto"
    if "fii" in raw_class or "reit" in raw_class or "fundos imobili" in sector:
        return "FIIs"
    if "etf" in raw_class:
        if currency not in {"", "BRL"} or country not in {"", "BR"} or "exterior" in sector:
            return "Global"
        return "ETFs"
    if currency not in {"", "BRL"} or country not in {"", "BR"} or region not in {"", "brasil", "brazil", "america latina"} or market in {"nasdaq", "nyse"}:
        return "Global"
    if "acao" in raw_class or "acoes" in raw_class or "aÃ§oes" in raw_class or "aÃ§Ãµes" in raw_class:
        return "Acoes Brasil"
    return "Outros"


def _apply_scenario(scenario: StressScenario, exposures: dict[str, float], total: float, passive_income: float) -> ScenarioResult:
    bucket_impacts = []
    total_impact = 0.0
    for bucket, value in exposures.items():
        shock = scenario.shocks.get(bucket, 0.0)
        impact = value * shock / 100
        after = max(0.0, value + impact)
        total_impact += impact
        if value > 0 or shock != 0:
            bucket_impacts.append(
                {
                    "bucket": bucket,
                    "before": round(value, 2),
                    "shockPct": round(shock, 2),
                    "impactValue": round(impact, 2),
                    "after": round(after, 2),
                }
            )
    stressed_equity = max(0.0, total + total_impact)
    impact_pct = total_impact / total * 100 if total else 0.0
    passive_after = max(0.0, passive_income * (1 + scenario.passive_income_shock / 100))
    passive_impact = passive_after - passive_income
    severity = _severity(impact_pct, scenario.passive_income_shock)
    return ScenarioResult(
        id=scenario.id,
        title=scenario.title,
        description=scenario.description,
        impactValue=round(total_impact, 2),
        impactPct=round(impact_pct, 2),
        severity=severity,
        reading=_scenario_reading(scenario, impact_pct, passive_impact),
        category=scenario.category,
        shockedEquity=round(total, 2),
        stressedEquity=round(stressed_equity, 2),
        passiveIncomeBefore=round(passive_income, 2),
        passiveIncomeAfter=round(passive_after, 2),
        passiveIncomeImpact=round(passive_impact, 2),
        bucketImpacts=bucket_impacts,
        assumptions=list(scenario.assumptions),
        recommendedActions=_recommended_actions(scenario, impact_pct, passive_impact),
        dataUsed=["portfolio.positions", "dashboard.metrics", "market_snapshots", "external_integrations"],
    )


def _severity(impact_pct: float, passive_shock: float) -> str:
    loss = abs(min(impact_pct, 0.0))
    income_loss = abs(min(passive_shock, 0.0))
    if loss >= 30 or income_loss >= 35:
        return "critica"
    if loss >= 18 or income_loss >= 20:
        return "alta"
    if loss >= 8 or income_loss >= 10:
        return "media"
    return "baixa"


def _scenario_reading(scenario: StressScenario, impact_pct: float, passive_impact: float) -> str:
    if scenario.id == "usd_brl_650" and impact_pct > 0:
        return f"Este choque pode ajudar a carteira em BRL se houver exposicao dolarizada; ainda assim aumenta risco macro e inflacao."
    if impact_pct <= -30:
        return "Cenario severo: a carteira precisaria de caixa, disciplina e revisao de concentracao para nao vender no pior momento."
    if passive_impact < 0:
        return "O ponto principal e proteger a meta de renda passiva, nao apenas olhar o valor patrimonial."
    return "Cenario de acompanhamento: mede sensibilidade sem representar previsao."


def _recommended_actions(scenario: StressScenario, impact_pct: float, passive_impact: float) -> list[str]:
    actions = []
    if impact_pct <= -20:
        actions.append("Revisar concentracao por classe e definir limite de perda suportavel antes de aumentar risco.")
    if scenario.category in {"cripto", "crise"}:
        actions.append("Manter cripto como exposicao pequena e separada do nucleo patrimonial.")
    if passive_impact < 0:
        actions.append("Simular meta de independencia financeira com renda passiva menor.")
    if scenario.category in {"juros", "inflacao"}:
        actions.append("Avaliar impacto de Selic/IPCA em FIIs, empresas alavancadas e valuation.")
    if scenario.category == "cambio":
        actions.append("Comparar exposicao global, BDR, ETF e stock direto antes de aumentar dolarizacao.")
    if not actions:
        actions.append("Usar o resultado como contexto para rebalanceamento e proximos aportes.")
    return actions


def _macro_context(db: Session, user_id: str) -> list[str]:
    try:
        snapshot = build_macro_fx_snapshot(db, user_id, refresh=False)
    except Exception:
        return ["Macro/FX indisponivel agora; stress test usou apenas posicoes e premissas internas."]
    rows = [snapshot.headline]
    for indicator in snapshot.indicators[:3]:
        rows.append(f"{indicator.title}: {indicator.value:.2f} {indicator.unit} ({indicator.status}).")
    for fx_rate in snapshot.fxRates[:2]:
        if fx_rate.rate:
            rows.append(f"{fx_rate.pair}: {fx_rate.rate:.4f} ({fx_rate.status}).")
    return rows[:6]


def _resilience_score(total: float, passive_income: float, exposures: dict[str, float], worst: ScenarioResult | None) -> float:
    if total <= 0 or worst is None:
        return 0.0
    worst_loss = abs(min(worst.impactPct, 0.0))
    crypto_weight = exposures.get("Cripto", 0.0) / total * 100 if total else 0
    global_value = exposures.get("Acoes Internacionais", 0.0) + exposures.get("ETFs Internacionais", 0.0) + exposures.get("REITs", 0.0)
    global_weight = global_value / total * 100 if total else 0
    income_weight = passive_income * 12 / total * 100 if total and passive_income else 0
    score = 100 - worst_loss * 1.55 - max(0.0, crypto_weight - 10) * 2.2 + min(10, global_weight * 0.35) + min(8, income_weight * 0.9)
    return round(max(0.0, min(100.0, score)), 2)


def _risk_level(score: float) -> str:
    if score >= 76:
        return "resiliente"
    if score >= 60:
        return "monitorado"
    if score >= 42:
        return "fragil_em_estresse"
    return "critico_em_estresse"


def _headline(score: float, worst: ScenarioResult | None) -> str:
    if worst is None:
        return "Stress Test aguardando patrimonio para simular cenarios."
    if score >= 76:
        return f"A carteira suporta melhor os choques simulados; pior impacto: {worst.title}."
    if score >= 60:
        return f"A carteira tem resiliencia moderada; principal stress: {worst.title}."
    return f"A carteira fica sensivel em crise; o pior cenario simulado foi {worst.title}."
