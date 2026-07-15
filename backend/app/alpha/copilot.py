from __future__ import annotations

from sqlalchemy.orm import Session

from app.alpha.contracts import CopilotQuestion, to_dict
from app.alpha.health_engine import calculate_health
from app.alpha.utils import money, percent
from app.services.portfolio import get_dashboard, get_positions


def build_copilot_interface(db: Session, user_id: str) -> dict:
    dashboard = get_dashboard(db, user_id)
    positions = get_positions(db, user_id)
    health = calculate_health(db, user_id)
    metrics = dashboard["metrics"]
    top_position = max(positions, key=lambda item: item["weight"], default=None)

    questions = [
        CopilotQuestion(
            id="financial_freedom_gap",
            pergunta="Quanto falta para minha liberdade financeira?",
            status="interface_pronta",
            respostaBase=(
                "A resposta usara renda passiva projetada, meta mensal, patrimonio atual e premissas de aporte."
            ),
        ),
        CopilotQuestion(
            id="risk_change",
            pergunta="Meu risco aumentou?",
            status="interface_pronta",
            respostaBase=f"A leitura atual usa Score Alpha {health.notaGeral:.0f}/100 e concentracao da carteira.",
        ),
        CopilotQuestion(
            id="score_drop_reason",
            pergunta="Por que meu score caiu?",
            status="interface_pronta",
            respostaBase="A resposta comparara historico de eventos, concentracao, valuation e fundamentos.",
        ),
        CopilotQuestion(
            id="monthly_contribution_need",
            pergunta="Quanto preciso aportar?",
            status="interface_pronta",
            respostaBase="A resposta usara meta, prazo, rentabilidade esperada e patrimonio atual.",
        ),
        CopilotQuestion(
            id="portfolio_explanation",
            pergunta="Explique minha carteira.",
            status="interface_pronta",
            respostaBase=(
                f"Carteira com {money(metrics['totalEquity'])}, retorno acumulado de {percent(metrics['pnlPct'])} "
                f"e renda passiva mensal projetada de {money(metrics['projectedPassiveIncome'])}."
            ),
        ),
        CopilotQuestion(
            id="largest_position",
            pergunta="Qual ativo pesa mais?",
            status="interface_pronta",
            respostaBase=(
                f"{top_position['ticker']} pesa {percent(top_position['weight'])} da carteira."
                if top_position
                else "Nao ha posicoes cadastradas para calcular o maior peso."
            ),
        ),
    ]

    return {
        "status": "preparado_sem_llm",
        "notaGeral": health.notaGeral,
        "contexto": {
            "patrimonioTotal": metrics["totalEquity"],
            "dividendosMes": metrics["dividendsMonth"],
            "rendaPassivaProjetada": metrics["projectedPassiveIncome"],
            "quantidadeAtivos": len(positions),
            "maiorAtivo": top_position["ticker"] if top_position else None,
            "maiorPeso": top_position["weight"] if top_position else 0,
        },
        "perguntas": to_dict(questions),
    }
