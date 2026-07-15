from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.model_portfolios import get_model_portfolios
from app.services.portfolio import get_allocations, get_dashboard, get_positions
from app.wealth_os.contracts import OpportunityStudy
from app.wealth_os.utils import as_float


def build_opportunities(db: Session, user_id: str) -> list[OpportunityStudy]:
    positions = get_positions(db, user_id)
    dashboard = get_dashboard(db, user_id)
    allocations = get_allocations(positions)
    total = as_float(dashboard["metrics"].get("totalEquity"))
    opportunities: list[OpportunityStudy] = []

    largest_asset = max(positions, key=lambda item: as_float(item.get("weight")), default=None)
    largest_class = max(allocations.get("byClass", []), key=lambda item: as_float(item.get("weight")), default=None)
    crypto_value = sum(as_float(item.get("currentValue")) for item in positions if str(item.get("class") or "").lower() in {"cripto", "crypto"})
    crypto_weight = crypto_value / total * 100 if total else 0

    if largest_asset and as_float(largest_asset.get("weight")) >= 18:
        opportunities.append(
            OpportunityStudy(
                id="concentration_review",
                title="Revisar concentracao individual",
                asset=largest_asset.get("ticker"),
                category="guardian",
                priority="alta",
                thesis=f"{largest_asset.get('ticker')} representa {as_float(largest_asset.get('weight')):.2f}% da carteira.",
                evidence=["Concentracao elevada aumenta impacto de uma noticia ruim no patrimonio.", "Guardian 2.0 prioriza risco antes de novos aportes concentrados."],
                risks=["Pode haver distorcao se o ativo for posicao temporaria.", "Nao e ordem automatica de venda."],
                nextStep="Avaliar se proximos aportes devem reduzir essa concentracao.",
                confidence="alta",
            )
        )

    if largest_class and largest_class.get("name") in {"Acoes", "Ações"} and as_float(largest_class.get("weight")) > 80:
        opportunities.append(
            OpportunityStudy(
                id="global_diversification_study",
                title="Estudar diversificacao global",
                asset=None,
                category="portfolio",
                priority="media",
                thesis="A carteira ainda depende muito de ativos locais e BRL.",
                evidence=["Asset Engine ja suporta pais, moeda, bolsa e exposicao.", "FMP e Twelve Data foram preparados para ativos internacionais."],
                risks=["Cambio pode aumentar volatilidade de curto prazo.", "Dividendos internacionais exigem leitura tributaria propria."],
                nextStep="Comparar stock, BDR e ETF global antes de abrir nova exposicao.",
                confidence="media",
            )
        )

    if crypto_weight > 10:
        opportunities.append(
            OpportunityStudy(
                id="crypto_weight_control",
                title="Controlar peso de cripto",
                asset=None,
                category="risco",
                priority="alta",
                thesis=f"Cripto esta em {crypto_weight:.2f}% da carteira consolidada.",
                evidence=["Classe tem alto potencial assimetrico.", "Classe tambem tem maior risco de queda brusca."],
                risks=["Aumentar peso sem limite pode prejudicar o plano principal.", "Nao substitui tese individual de cada moeda."],
                nextStep="Usar o Crypto Research Engine para diferenciar oportunidade real de especulacao fraca.",
                confidence="media",
            )
        )

    try:
        portfolios = get_model_portfolios(db, user_id=user_id, refresh_market=False)
        alpha = portfolios.get("alphaRecommended", {})
        candidate = (alpha.get("assets") or [None])[0]
        if candidate:
            opportunities.append(
                OpportunityStudy(
                    id="alpha_recommended_next_study",
                    title="Carteira Recomendada Alpha em estudo",
                    asset=candidate.get("ticker"),
                    category="carteira_recomendada",
                    priority="media",
                    thesis=f"{candidate.get('ticker')} aparece entre os ativos melhor classificados pelo Screener Alpha B3.",
                    evidence=[
                        "Passou por filtros de setor, fundamentos e papel na carteira.",
                        "A tela de Carteira Recomendada traz pesos, tese e pontos de acompanhamento.",
                    ],
                    risks=["Confirmar preco, liquidez e dados fundamentalistas antes de aumentar exposicao.", "Nao concentrar tudo em um unico ativo."],
                    nextStep="Abrir a Carteira Recomendada e comparar com sua alocacao atual.",
                    confidence="media",
                )
            )
    except Exception:
        pass

    if not opportunities:
        opportunities.append(
            OpportunityStudy(
                id="maintain_plan",
                title="Manter plano e melhorar dados",
                asset=None,
                category="processo",
                priority="media",
                thesis="Nenhum alerta forte apareceu com os dados atuais.",
                evidence=["Carteira sem concentracao extrema identificada.", "Motores internos conseguiram calcular a leitura basica."],
                risks=["Dados incompletos podem esconder oportunidades ou riscos.", "Mercado muda; a leitura precisa ser recorrente."],
                nextStep="Sincronizar mercado, registrar proventos e revisar no proximo ciclo.",
                confidence="media",
            )
        )
    return opportunities[:5]

