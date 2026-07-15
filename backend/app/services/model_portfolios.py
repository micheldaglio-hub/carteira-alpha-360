from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.asset_engine import ensure_asset_engine_metadata
from app.models import Asset
from app.services.alpha_confidence_engine import build_alpha_confidence_report
from app.services.alpha_b3_screener import run_alpha_b3_screener
from app.services.alpha_crypto_screener import run_alpha_crypto_screener
from app.services.alpha_fii_screener import run_alpha_fii_screener
from app.services.alpha_global_equity_screener import run_alpha_global_equity_screener
from app.services.data_confidence_engine import build_data_confidence_audit
from app.services.global_backtest import run_global_backtest
from app.services.market_data.sync import sync_asset_market_data
from app.services.recommendation_governance_engine import build_recommendation_governance
from app.services.recommended_portfolio_engine import build_recommended_portfolio_report
from app.services.scoring import (
    dividend_score,
    risk_score,
    safety_score,
    valuation_score,
)
from app.wealth_os.contracts import to_dict
from app.wealth_os.strategy_engine import build_strategy_report


DIVIDEND_MODEL_ASSETS = [
    {
        "ticker": "BBSE3",
        "name": "BB Seguridade",
        "sector": "Seguros",
        "class": "Acoes",
        "targetWeight": 15,
        "riskLevel": "moderado",
        "role": "Renda passiva e resiliencia",
        "thesis": "Seguradora com alta rentabilidade, historico de dividendos e exposicao a um setor defensivo em ambiente de juros elevados.",
        "watchpoints": ["Dependencia do Banco do Brasil", "Mudancas regulatorias", "Competicao em seguros e previdencia"],
    },
    {
        "ticker": "BBAS3",
        "name": "Banco do Brasil",
        "sector": "Bancos",
        "class": "Acoes",
        "targetWeight": 15,
        "riskLevel": "moderado",
        "role": "Banco perene com valuation descontado",
        "thesis": "Banco de grande escala, forte presenca no agronegocio, ROE elevado e multiplos historicamente atrativos.",
        "watchpoints": ["Risco de interferencia estatal", "Ciclo de credito", "Inadimplencia no agro e varejo"],
    },
    {
        "ticker": "TAEE11",
        "name": "Taesa",
        "sector": "Energia",
        "class": "Acoes",
        "targetWeight": 10,
        "riskLevel": "baixo_moderado",
        "role": "Previsibilidade de receita",
        "thesis": "Transmissora de energia com contratos de longo prazo, baixa exposicao a demanda e perfil historico de dividendos.",
        "watchpoints": ["Revisoes regulatorias", "Custo de capital", "Vencimento de concessoes"],
    },
    {
        "ticker": "EGIE3",
        "name": "Engie Brasil",
        "sector": "Energia",
        "class": "Acoes",
        "targetWeight": 10,
        "riskLevel": "baixo_moderado",
        "role": "Qualidade e energia renovavel",
        "thesis": "Geradora privada com ativos de qualidade, gestao eficiente e foco em energia renovavel.",
        "watchpoints": ["Risco hidrologico", "Preco de energia", "Alavancagem para expansao"],
    },
    {
        "ticker": "AURE3",
        "name": "Auren Energia",
        "sector": "Energia",
        "class": "Acoes",
        "targetWeight": 10,
        "riskLevel": "moderado",
        "role": "Energia com potencial de crescimento",
        "thesis": "Companhia de energia com foco em renovaveis, contratos de longo prazo e potencial de expansao.",
        "watchpoints": ["Dividendos extraordinarios podem distorcer DY", "Risco hidrologico", "Retorno sobre capital ainda em maturacao"],
    },
    {
        "ticker": "CMIG4",
        "name": "Cemig",
        "sector": "Energia",
        "class": "Acoes",
        "targetWeight": 8,
        "riskLevel": "moderado_alto",
        "role": "Yield elevado com risco politico",
        "thesis": "Empresa integrada de energia com base relevante de ativos e historico de dividendos, mas com risco politico maior.",
        "watchpoints": ["Interferencia politica", "Regulacao", "Risco hidrologico e necessidade de investimento"],
    },
    {
        "ticker": "CSMG3",
        "name": "Copasa",
        "sector": "Saneamento",
        "class": "Acoes",
        "targetWeight": 8,
        "riskLevel": "moderado",
        "role": "Setor essencial",
        "thesis": "Saneamento e servico essencial, com concessoes longas e potencial de eficiencia com o marco legal do setor.",
        "watchpoints": ["Risco politico estadual", "Capex elevado", "Qualidade regulatoria"],
    },
    {
        "ticker": "BRSR6",
        "name": "Banrisul",
        "sector": "Bancos",
        "class": "Acoes",
        "targetWeight": 8,
        "riskLevel": "moderado_alto",
        "role": "Banco regional descontado",
        "thesis": "Banco regional com multiplos descontados e historico de dividendos, mas com concentracao geografica relevante.",
        "watchpoints": ["Concentracao no Rio Grande do Sul", "Risco politico", "Competicao bancaria"],
    },
    {
        "ticker": "CPLE6",
        "name": "Copel",
        "sector": "Energia",
        "class": "Acoes",
        "targetWeight": 8,
        "riskLevel": "moderado",
        "role": "Energia pos-privatizacao",
        "thesis": "Empresa de energia com potencial de eficiencia operacional apos privatizacao e diversificacao entre geracao, transmissao e distribuicao.",
        "watchpoints": ["Execucao pos-privatizacao", "Regulacao", "Risco hidrologico"],
    },
    {
        "ticker": "BBDC4",
        "name": "Bradesco",
        "sector": "Bancos",
        "class": "Acoes",
        "targetWeight": 8,
        "riskLevel": "moderado",
        "role": "Recuperacao bancaria",
        "thesis": "Banco privado de grande escala em fase de recuperacao de rentabilidade e eficiencia operacional.",
        "watchpoints": ["Recuperacao de ROE", "Inadimplencia", "Competicao de fintechs"],
    },
]


SPICE_ASSETS = [
    {
        "ticker": "PRNR3",
        "name": "Priner",
        "sector": "Engenharia industrial e infraestrutura",
        "suggestedBand": "0% a 5%",
        "riskLevel": "alto",
        "role": "Pimenta de crescimento",
        "thesis": "Empresa de engenharia industrial com historico de aquisicoes e exposicao a clientes relevantes de setores como oleo e gas, mineracao e papel e celulose.",
        "watchpoints": ["Dependencia de grandes projetos", "Custo de capital alto", "Ciclos de infraestrutura e commodities"],
    },
    {
        "ticker": "TTEN3",
        "name": "3tentos",
        "sector": "Agronegocio integrado",
        "suggestedBand": "0% a 5%",
        "riskLevel": "alto",
        "role": "Pimenta ligada ao agro",
        "thesis": "Modelo verticalizado no agronegocio, com historico de crescimento e exposicao a um setor estrutural da economia brasileira.",
        "watchpoints": ["Clima", "Precos de commodities agricolas", "Endividamento para expansao"],
    },
]


BACKTEST_ROWS = [
    {"month": "2025-01", "stockPortfolio": 1013.43, "fixedIncome": 1010.00, "monthlyReturn": 1.34},
    {"month": "2025-02", "stockPortfolio": 1040.76, "fixedIncome": 1020.10, "monthlyReturn": 2.70},
    {"month": "2025-03", "stockPortfolio": 1075.62, "fixedIncome": 1030.30, "monthlyReturn": 3.35},
    {"month": "2025-04", "stockPortfolio": 1084.64, "fixedIncome": 1040.60, "monthlyReturn": 0.84},
    {"month": "2025-05", "stockPortfolio": 1103.23, "fixedIncome": 1051.01, "monthlyReturn": 1.71},
    {"month": "2025-06", "stockPortfolio": 1114.43, "fixedIncome": 1061.52, "monthlyReturn": 1.02},
    {"month": "2025-07", "stockPortfolio": 1133.47, "fixedIncome": 1072.14, "monthlyReturn": 1.71},
    {"month": "2025-08", "stockPortfolio": 1142.54, "fixedIncome": 1082.86, "monthlyReturn": 0.80},
    {"month": "2025-09", "stockPortfolio": 1168.69, "fixedIncome": 1093.69, "monthlyReturn": 2.29},
    {"month": "2025-10", "stockPortfolio": 1175.07, "fixedIncome": 1104.62, "monthlyReturn": 0.55},
    {"month": "2025-11", "stockPortfolio": 1202.91, "fixedIncome": 1115.67, "monthlyReturn": 2.37},
    {"month": "2025-12", "stockPortfolio": 1232.20, "fixedIncome": 1126.83, "monthlyReturn": 2.43},
    {"month": "2026-01", "stockPortfolio": 1259.46, "fixedIncome": 1138.09, "monthlyReturn": 2.21},
    {"month": "2026-02", "stockPortfolio": 1273.95, "fixedIncome": 1149.47, "monthlyReturn": 1.15},
    {"month": "2026-03", "stockPortfolio": 1266.26, "fixedIncome": 1160.97, "monthlyReturn": -0.60},
    {"month": "2026-04", "stockPortfolio": 1286.90, "fixedIncome": 1172.58, "monthlyReturn": 1.63},
    {"month": "2026-05", "stockPortfolio": 1303.89, "fixedIncome": 1184.30, "monthlyReturn": 1.32},
    {"month": "2026-06", "stockPortfolio": 1317.83, "fixedIncome": 1196.15, "monthlyReturn": 1.07},
    {"month": "2026-07", "stockPortfolio": 1313.93, "fixedIncome": 1208.11, "monthlyReturn": -0.30},
]


PERENNIAL_SECTORS = {
    "energia": 92,
    "bancos": 82,
    "seguros": 88,
    "saneamento": 90,
}


def _float(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0


def _manual_risk_score(risk_level: str) -> float:
    return {
        "baixo": 92,
        "baixo_moderado": 84,
        "moderado": 72,
        "moderado_alto": 58,
        "alto": 42,
        "extremo": 20,
    }.get(risk_level, 60)


def _data_quality(snapshot) -> tuple[str, int, float]:
    if snapshot is None:
        return "sem_dados", 0, 0
    fields = [
        snapshot.price,
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
        snapshot.dividend_consistency,
        snapshot.recurring_profit,
        snapshot.sector_stability,
    ]
    filled = sum(1 for value in fields if abs(_float(value)) > 0)
    score = min(100, round(filled / 10 * 100, 2))
    if filled >= 8:
        status = "completa"
    elif filled >= 5:
        status = "parcial"
    else:
        status = "insuficiente"
    return status, filled, score


def _sector_score(sector: str) -> float:
    normalized = sector.lower()
    for key, score in PERENNIAL_SECTORS.items():
        if key in normalized:
            return score
    return 58


def _allocation_score(target_weight: float, sector_weight: float) -> tuple[float, list[str]]:
    notes = []
    score = 88
    if target_weight > 15:
        score -= 18
        notes.append("Peso por ativo acima de 15% exige justificativa adicional.")
    elif target_weight >= 12:
        notes.append("Peso relevante; acompanhar concentracao individual.")
    if sector_weight > 45:
        score -= 16
        notes.append("Setor acima de 45% aumenta concentracao tematica.")
    if not notes:
        notes.append("Peso individual e setorial dentro dos limites iniciais.")
    return max(0, score), notes


def _status_from(score: float, data_status: str, risk: float) -> str:
    if data_status in {"sem_dados", "insuficiente"}:
        return "dados_insuficientes"
    if data_status == "parcial" and score < 62:
        return "em_observacao"
    if score >= 76 and risk <= 48:
        return "validado_alpha"
    if score >= 62:
        return "em_observacao"
    return "reprovado_alpha"


def _status_label(status: str) -> str:
    return {
        "validado_alpha": "Validado pelo Alpha",
        "em_observacao": "Em observacao",
        "reprovado_alpha": "Reprovado pelo Alpha",
        "dados_insuficientes": "Dados insuficientes",
    }.get(status, status)


def _ensure_model_asset(db: Session, item: dict) -> Asset:
    asset = db.execute(select(Asset).where(Asset.ticker == item["ticker"])).scalar_one_or_none()
    if asset is not None:
        return asset
    asset = Asset(
        ticker=item["ticker"],
        name=item["name"],
        asset_class=item.get("class", "Acoes"),
        sector=item.get("sector", "Nao classificado"),
        segment="Carteira recomendada",
        currency="BRL",
        provider_symbol=item["ticker"],
        last_price=Decimal("0"),
    )
    ensure_asset_engine_metadata(db, asset, force=True)
    db.add(asset)
    db.flush()
    return asset


def validate_dividend_portfolio(db: Session, *, refresh_market: bool = False) -> dict:
    sector_weights: dict[str, float] = {}
    for item in DIVIDEND_MODEL_ASSETS:
        sector_weights[item["sector"]] = sector_weights.get(item["sector"], 0) + float(item["targetWeight"])

    rows = []
    updated = []
    skipped = []
    for item in DIVIDEND_MODEL_ASSETS:
        asset = _ensure_model_asset(db, item)
        if refresh_market:
            try:
                if sync_asset_market_data(db, asset):
                    updated.append(asset.ticker)
                else:
                    skipped.append(asset.ticker)
            except Exception:
                skipped.append(asset.ticker)

        snapshot = asset.snapshot
        data_status, data_fields, data_score = _data_quality(snapshot)
        if snapshot is not None:
            div, div_reasons = dividend_score(snapshot)
            safety = safety_score(snapshot)
            valuation = valuation_score(snapshot)
            risk = risk_score(snapshot)
        else:
            div = safety = valuation = 0
            risk = 100
            div_reasons = ["Sem snapshot de mercado suficiente para validar dividendos."]

        sector = _sector_score(item["sector"])
        manual_risk = _manual_risk_score(item["riskLevel"])
        allocation, allocation_notes = _allocation_score(float(item["targetWeight"]), sector_weights[item["sector"]])
        final_score = round(
            div * 0.22
            + safety * 0.20
            + valuation * 0.14
            + (100 - risk) * 0.14
            + data_score * 0.12
            + sector * 0.08
            + manual_risk * 0.05
            + allocation * 0.05,
            2,
        )
        status = _status_from(final_score, data_status, risk)
        blockers = []
        if data_status in {"sem_dados", "insuficiente"}:
            blockers.append("Faltam dados atuais suficientes para validacao independente.")
        if risk > 58:
            blockers.append("Risco quantitativo acima da faixa desejada.")
        if valuation < 35 and data_status not in {"sem_dados", "insuficiente"}:
            blockers.append("Valuation exige atencao antes de aumentar peso.")
        if sector_weights[item["sector"]] > 45:
            blockers.append("Concentracao setorial acima da faixa conservadora.")

        rows.append(
            {
                "ticker": asset.ticker,
                "name": asset.name,
                "sector": item["sector"],
                "targetWeight": item["targetWeight"],
                "status": status,
                "statusLabel": _status_label(status),
                "validationScore": final_score,
                "dataStatus": data_status,
                "dataFields": data_fields,
                "scores": {
                    "dividends": round(div, 2),
                    "safety": round(safety, 2),
                    "valuation": round(valuation, 2),
                    "risk": round(risk, 2),
                    "dataQuality": round(data_score, 2),
                    "sector": round(sector, 2),
                    "allocation": round(allocation, 2),
                },
                "reading": (
                    f"{asset.ticker} esta {_status_label(status).lower()}. "
                    f"Score {final_score}/100, dados {data_status}, risco {round(risk, 2)}/100."
                ),
                "evidence": [
                    *div_reasons[:2],
                    f"Seguranca {round(safety, 2)}/100, valuation {round(valuation, 2)}/100 e qualidade de dados {round(data_score, 2)}/100.",
                    *allocation_notes,
                ],
                "blockers": blockers,
            }
        )

    validated = sum(1 for item in rows if item["status"] == "validado_alpha")
    observation = sum(1 for item in rows if item["status"] == "em_observacao")
    rejected = sum(1 for item in rows if item["status"] == "reprovado_alpha")
    insufficient = sum(1 for item in rows if item["status"] == "dados_insuficientes")
    overall_score = round(sum(item["validationScore"] for item in rows) / len(rows), 2) if rows else 0
    if insufficient:
        status = "em_validacao"
        label = "Validacao parcial"
    elif rejected:
        status = "requer_ajustes"
        label = "Requer ajustes"
    elif validated >= 7 and overall_score >= 72:
        status = "validada_alpha"
        label = "Validada pelo Alpha"
    else:
        status = "em_observacao"
        label = "Em observacao"

    if refresh_market:
        db.commit()

    return {
        "status": status,
        "label": label,
        "message": "Validacao Alpha calculada com os dados atuais disponiveis no sistema.",
        "nextStep": (
            "Acompanhar ativos em observacao, completar dados insuficientes e atualizar fontes externas antes de marcar como carteira definitiva."
            if status != "validada_alpha"
            else "Carteira passou nos criterios atuais do Alpha. Continuar revisao periodica mensal."
        ),
        "overallScore": overall_score,
        "validatedCount": validated,
        "observationCount": observation,
        "rejectedCount": rejected,
        "insufficientCount": insufficient,
        "updatedTickers": updated,
        "skippedTickers": skipped,
        "criteria": [
            "Dados atuais suficientes.",
            "Dividendos consistentes e sustentaveis.",
            "Seguranca financeira e baixa alavancagem relativa.",
            "Valuation dentro de faixa aceitavel.",
            "Risco quantitativo controlado.",
            "Concentracao individual e setorial dentro da politica.",
        ],
        "rows": sorted(rows, key=lambda item: item["validationScore"], reverse=True),
    }


def get_model_portfolios(db: Session | None = None, *, user_id: str | None = None, refresh_market: bool = False) -> dict:
    screener = run_alpha_b3_screener(db, refresh_market=refresh_market)
    fii_screener = run_alpha_fii_screener(db, refresh_market=refresh_market)
    global_screener = run_alpha_global_equity_screener(db, refresh_market=refresh_market)
    global_backtest = run_global_backtest(db, refresh_market=False, global_portfolio=global_screener["portfolio"])
    crypto_study = run_alpha_crypto_screener(db, user_id, refresh_market=refresh_market)
    validation = _validation_from_screener(screener)
    dividend_assets = deepcopy(screener["portfolio"])
    spice_assets = deepcopy(SPICE_ASSETS)
    backtest_rows = deepcopy(BACKTEST_ROWS)

    sector_allocation: dict[str, float] = {}
    for asset in dividend_assets:
        sector_allocation[asset["sector"]] = sector_allocation.get(asset["sector"], 0) + asset["targetWeight"]

    backtest = {
        "title": "Backtest importado: carteira de acoes versus renda fixa",
        "period": "2025-01 a 2026-07",
        "initialValue": 1000,
        "assumptions": [
            "Carteira de acoes com dividendos reinvestidos conforme relatorio importado.",
            "Renda fixa simulada a 1% ao mes.",
            "Resultado historico nao garante repeticao futura.",
        ],
        "summary": {
            "stockFinalValue": 1313.93,
            "fixedIncomeFinalValue": 1208.11,
            "extraProfit": 105.82,
            "stockTotalReturn": 31.39,
            "fixedIncomeTotalReturn": 20.81,
        },
        "rows": backtest_rows,
    }
    confidence_report = build_alpha_confidence_report(
        screener=screener,
        validation=validation,
        fii_screener=fii_screener,
        global_screener=global_screener,
        crypto_study=crypto_study,
        global_backtest=global_backtest,
        imported_backtest=backtest,
    )
    strategy_report = {}
    data_confidence_audit = {}
    if db is not None and user_id:
        try:
            strategy_report = to_dict(build_strategy_report(db, user_id))
        except Exception:
            strategy_report = {}
        try:
            data_confidence_audit = build_data_confidence_audit(db, user_id)
        except Exception:
            data_confidence_audit = {}
    recommended_report = build_recommended_portfolio_report(
        screener=screener,
        validation=validation,
        confidence_report=confidence_report,
        fii_screener=fii_screener,
        global_screener=global_screener,
        crypto_study=crypto_study,
        global_backtest=global_backtest,
        strategy_report=strategy_report,
    )
    recommendation_governance = build_recommendation_governance(
        db,
        user_id,
        recommended_report,
        confidence_report,
        data_confidence_audit,
    )
    recommended_report["governanceLedgerV2"] = recommendation_governance

    return {
        "status": "educational_model",
        "updatedAt": "2026-07-11",
        "source": "Carteira gerada pelo Screener Alpha B3 com universo B3, filtros de setores perenes e leitura proprietaria.",
        "screener": screener,
        "validation": validation,
        "confidenceReport": confidence_report,
        "dataConfidenceAudit": data_confidence_audit,
        "recommendedPortfolioReport": recommended_report,
        "recommendationGovernance": recommendation_governance,
        "disclaimer": (
            "Conteudo analitico para estudo. Nao representa recomendacao individual, ordem de compra ou venda, "
            "promessa de rentabilidade ou garantia de resultado."
        ),
        "methodology": [
            "Separar carteira principal de proventos, FIIs e ativos de maior risco.",
            "Priorizar setores perenes: energia, bancos, saneamento, seguros e renda imobiliaria.",
            "Usar pesos-alvo como referencia de estudo, nao como ordem operacional.",
            "Comparar cenarios historicos com renda fixa para entender risco, volatilidade e retorno.",
            "Manter cripto e small caps como exposicoes controladas, fora do nucleo patrimonial.",
        ],
        "macroContext": {
            "title": "Premissas de mercado usadas pelo Screener Alpha",
            "points": [
                "Juros elevados favorecem caixa, bancos e seguradoras, mas pressionam valuation de crescimento.",
                "Energia e saneamento tendem a ter receitas mais defensivas, mas exigem atencao a regulacao e politica.",
                "Proventos devem ser avaliados por consistencia, payout, caixa, qualidade do lucro e qualidade do ativo, nao apenas pelo DY.",
            ],
        },
        "dividendPortfolio": {
            "id": "carteira-recomendada-alpha-oficial-2026-07-11",
            "title": "Carteira Recomendada Alpha oficial",
            "profile": "Renda passiva, preservacao patrimonial e setores essenciais selecionados pelo Screener Alpha B3",
            "targetReturnLanguage": "Busca consistencia de renda e qualidade, sem promessa de rentabilidade.",
            "assets": dividend_assets,
            "sectorAllocation": [{"name": name, "value": value} for name, value in sorted(sector_allocation.items())],
        },
        "fiiPortfolio": {
            "id": "carteira-alpha-fiis-proventos-2026-07-12",
            "title": "Carteira Alpha FIIs - estudo inicial",
            "profile": "Renda imobiliaria em validacao, proventos mensais, diversificacao por segmento e risco controlado",
            "targetReturnLanguage": "Estudo inicial de renda imobiliaria; nao representa varredura completa de todos os FIIs, promessa de rentabilidade ou isencao tributaria garantida.",
            "assets": fii_screener["portfolio"],
            "segmentAllocation": fii_screener["segmentAllocation"],
            "taxNote": fii_screener["taxNote"],
            "dataNote": fii_screener["dataNote"],
            "filters": fii_screener["filters"],
            "validationNote": "O motor de FIIs foi criado como fundacao. Ainda precisa de historico real de vacancia, P/VP, rendimentos e liquidez por provider para virar varredura completa.",
        },
        "fiiScreener": fii_screener,
        "globalPortfolio": {
            "id": "carteira-alpha-global-equities-2026-07-12",
            "title": "Carteira Alpha Global - watchlist inicial",
            "profile": "Acoes internacionais de qualidade para diversificacao geografica, setorial e cambial",
            "targetReturnLanguage": "Watchlist global em validacao; nao representa varredura completa de todas as bolsas do mundo.",
            "assets": global_screener["portfolio"],
            "regionAllocation": global_screener["regionAllocation"],
            "currencyAllocation": global_screener["currencyAllocation"],
            "sectorAllocation": global_screener["sectorAllocation"],
            "filters": global_screener["filters"],
            "validationNote": global_screener["validationNote"],
            "nextSteps": global_screener["nextSteps"],
        },
        "globalScreener": global_screener,
        "globalBacktest": global_backtest,
        "spicePortfolio": {
            "id": "pimentas-crescimento-jul-2026",
            "title": "Ativos pimenta para estudo",
            "maxSuggestedExposure": "5% a 10% da carteira total, conforme tolerancia a risco.",
            "riskWarning": "Ativos de alto risco podem cair forte, ficar anos sem performar ou perder capital.",
            "assets": spice_assets,
        },
        "backtest": backtest,
        "cryptoStudy": crypto_study,
    }


def _validation_from_screener(screener: dict) -> dict:
    rows = [
        {
            "ticker": asset["ticker"],
            "name": asset["name"],
            "sector": asset["sector"],
            "targetWeight": asset["targetWeight"],
            "status": "selected_alpha",
            "statusLabel": asset["alphaReading"].split(":")[0],
            "validationScore": asset["alphaScore"],
            "dataStatus": "analisado",
            "dataFields": asset.get("dataFields", 0),
            "reading": asset["alphaReading"],
            "evidence": asset.get("whySelected", []),
            "blockers": [],
        }
        for asset in screener["portfolio"]
    ]
    overall_score = round(sum(row["validationScore"] for row in rows) / len(rows), 2) if rows else 0
    return {
        "status": "carteira_alpha_oficial",
        "label": "Carteira Alpha oficial",
        "message": "Carteira gerada pelo Screener Alpha B3 com filtros de setores perenes, qualidade, dividendos, liquidez e risco.",
        "nextStep": "Revisar mensalmente com novas fontes, resultados trimestrais, dividendos e mudancas macroeconomicas.",
        "overallScore": overall_score,
        "validatedCount": len(rows),
        "observationCount": 0,
        "rejectedCount": 0,
        "insufficientCount": 0,
        "updatedTickers": [],
        "skippedTickers": [],
        "criteria": screener["filters"],
        "rows": rows,
    }
