from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.alpha.alpha_score_engine import calculate_alpha_scores_v2
from app.alpha.contracts import AlphaEvent, Insight
from app.alpha.health_engine import calculate_health
from app.alpha.utils import money, percent
from app.services.portfolio import get_allocations, get_dashboard, get_positions


def _insight(
    titulo: str,
    descricao: str,
    *,
    prioridade: str,
    tipo: str,
    impacto: str,
    data: datetime | None = None,
) -> Insight:
    return Insight(
        titulo=titulo,
        descricao=descricao,
        prioridade=prioridade,
        tipo=tipo,
        impacto=impacto,
        data=(data or datetime.utcnow()).isoformat(),
    )


def build_insights(db: Session, user_id: str, events: list[AlphaEvent] | None = None) -> list[Insight]:
    positions = get_positions(db, user_id)
    allocations = get_allocations(positions)
    dashboard = get_dashboard(db, user_id)
    health = calculate_health(db, user_id)
    alpha_scores = calculate_alpha_scores_v2(db, user_id)
    insights: list[Insight] = []

    if positions:
        top_position = max(positions, key=lambda item: item["weight"])
        if top_position["weight"] >= 20:
            insights.append(
                _insight(
                    f"{top_position['ticker']} tem peso elevado",
                    f"{top_position['ticker']} representa {percent(top_position['weight'])} da carteira.",
                    prioridade="alta" if top_position["weight"] >= 30 else "media",
                    tipo="risco",
                    impacto="Pode aumentar a sensibilidade da carteira a um unico ativo.",
                )
            )

    if allocations["bySector"]:
        top_sector = allocations["bySector"][0]
        if top_sector["weight"] >= 35:
            insights.append(
                _insight(
                    f"Carteira concentrada em {top_sector['name']}",
                    f"O setor {top_sector['name']} representa {percent(top_sector['weight'])} do patrimonio.",
                    prioridade="alta" if top_sector["weight"] >= 45 else "media",
                    tipo="risco",
                    impacto="A concentracao setorial pode ampliar os efeitos de ciclos especificos.",
                )
            )

    metrics = dashboard["metrics"]
    if metrics["dividendsMonth"] > 0:
        insights.append(
            _insight(
                "Renda passiva registrada no mes",
                f"A carteira recebeu {money(metrics['dividendsMonth'])} em proventos no mes corrente.",
                prioridade="media",
                tipo="renda",
                impacto="Reforca o acompanhamento da estrategia de fluxo de caixa.",
            )
        )

    if metrics["projectedPassiveIncome"] > 0:
        insights.append(
            _insight(
                "Renda passiva mensal projetada",
                f"A renda passiva mensal estimada esta em {money(metrics['projectedPassiveIncome'])}.",
                prioridade="baixa",
                tipo="renda",
                impacto="Cenario calculado com os yields atuais dos ativos.",
            )
        )

    if health.notaGeral < 58:
        insights.append(
            _insight(
                "Carteira em fase de construcao",
                f"A nota geral esta em {health.notaGeral:.0f}/100. Isso indica que o Alpha ainda esta acompanhando dados, pesos e historico antes de dar uma leitura mais forte.",
                prioridade="alta" if health.notaGeral < 45 else "media",
                tipo="score",
                impacto="Nao significa que a carteira recomendada esteja errada; significa que a leitura precisa de mais dados e acompanhamento.",
            )
        )
    elif health.notaGeral >= 75:
        insights.append(
            _insight(
                "Score Alpha em faixa saudavel",
                f"A nota geral da carteira esta em {health.notaGeral:.0f}/100.",
                prioridade="media",
                tipo="score",
                impacto="A leitura agregada mostra boa qualidade relativa dos fatores internos.",
            )
        )

    if alpha_scores:
        strongest = alpha_scores[0]
        weakest = alpha_scores[-1]
        insights.append(
            _insight(
                f"{strongest.ticker} lidera o Score Alpha 2.0",
                f"{strongest.ticker} aparece com {strongest.scoreFinal:.0f}/100 e classificacao {strongest.classificacao}.",
                prioridade="baixa",
                tipo="qualidade",
                impacto="Ajuda a entender quais ativos mais contribuem para a leitura qualitativa.",
            )
        )
        if weakest.scoreFinal < 45:
            insights.append(
                _insight(
                    f"{weakest.ticker} entrou em revisao do Alpha",
                    f"{weakest.ticker} marca {weakest.scoreFinal:.0f}/100 no Score Alpha 2.0 e precisa de acompanhamento da tese.",
                    prioridade="media",
                    tipo="qualidade",
                    impacto="A leitura aponta ponto de atencao, nao ordem automatica de venda.",
                )
            )

    for event in events or []:
        if event.tipo in {"novo_maior_patrimonio", "patrimonio_bateu_recorde"}:
            insights.append(
                _insight(
                    "Patrimonio em novo recorde interno",
                    event.descricao,
                    prioridade="media",
                    tipo="patrimonio",
                    impacto=event.impacto,
                )
            )
            break

    priority_rank = {"alta": 0, "media": 1, "baixa": 2}
    return sorted(insights, key=lambda item: priority_rank.get(item.prioridade, 9))[:10]
