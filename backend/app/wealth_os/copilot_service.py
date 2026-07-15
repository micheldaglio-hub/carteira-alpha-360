from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.portfolio_aggregation import build_user_portfolio_snapshot
from app.services.portfolio import get_dashboard, get_positions
from app.wealth_os.contracts import CopilotChatResponse, CopilotCitation, CopilotQuestion, to_dict
from app.wealth_os.data_confidence_engine import build_data_confidence
from app.wealth_os.economic_engine import build_economic_readings
from app.wealth_os.goal_engine import build_goals
from app.wealth_os.guardian_engine import build_guardian_report
from app.wealth_os.scenario_engine import build_stress_test_report
from app.wealth_os.strategy_engine import build_strategy_report
from app.wealth_os.utils import as_float
from app.wealth_os.wealth_progress_engine import build_wealth_progress_score


COPILOT_RULES = [
    "Responder apenas com dados internos fornecidos pelo backend.",
    "Citar as fontes internas usadas em cada conclusao relevante.",
    "Declarar lacunas quando os dados forem insuficientes.",
    "Nao prometer rentabilidade, nao prever preco e nao emitir ordem direta de compra ou venda.",
    "Usar linguagem humana, objetiva e operacional.",
]


def build_copilot_questions(db: Session, user_id: str) -> list[CopilotQuestion]:
    context = build_copilot_context(db, user_id)
    metrics = context["summary"]
    portfolio_snapshot = context.get("portfolioSnapshot") or {}
    largest = (portfolio_snapshot.get("largest") or {}).get("asset") or (context["positions"][0] if context["positions"] else None)
    goals = {goal["id"]: goal for goal in context["goals"]}
    positions = context["positions"]
    passive_goal = goals.get("passive_income")
    missing_income = as_float(passive_goal.get("remainingValue")) if passive_goal else 0
    months = passive_goal.get("estimatedMonths") if passive_goal else None
    largest_answer = (
        f"O ativo que mais pesa hoje e {largest.get('name')}, com {as_float(largest.get('weight')):.2f}% da carteira."
        if largest
        else "Ainda nao ha posicoes suficientes para apontar o ativo de maior peso."
    )

    return [
        CopilotQuestion(
            id="financial_freedom_gap",
            question="Quanto falta para minha liberdade financeira?",
            category="metas",
            answer=(
                f"Sua renda passiva mensal projetada esta em R$ {as_float(metrics.get('projectedPassiveIncome')):,.2f}. "
                f"Faltam R$ {missing_income:,.2f} por mes para a meta cadastrada."
            ),
            dataUsed=["dashboard.metrics.projectedPassiveIncome", "goal_engine.passive_income"],
            confidence="media",
        ),
        CopilotQuestion(
            id="risk_changed",
            question="Meu risco aumentou?",
            category="guardian",
            answer="O risco e acompanhado por concentracao, peso de cripto, setores, stress test e Wealth Progress Score. Use o Guardian para ver os pontos abertos antes de alterar a carteira.",
            dataUsed=["portfolio.positions", "guardian", "stress_test", "wealth_progress_score"],
            confidence="media",
        ),
        CopilotQuestion(
            id="score_drop_reason",
            question="Por que meu score caiu?",
            category="score",
            answer="As causas mais comuns sao concentracao, dados incompletos, queda no P/L da carteira, aumento de cripto ou piora de fatores de saude. O Alpha mostra os fatores que puxam a nota.",
            dataUsed=["wealth_progress_score.factors", "guardian", "data_confidence"],
            confidence="media",
        ),
        CopilotQuestion(
            id="monthly_contribution_needed",
            question="Quanto preciso aportar?",
            category="metas",
            answer=(
                f"Pela meta de renda passiva, o tempo estimado esta em {months} meses."
                if months is not None
                else "Ainda faltam premissas de aporte, yield e retorno para estimar o aporte ideal."
            ),
            dataUsed=["goal_engine", "projection_premises"],
            confidence="media",
        ),
        CopilotQuestion(
            id="explain_portfolio",
            question="Explique minha carteira.",
            category="portfolio",
            answer=(
                f"Sua carteira consolidada esta em R$ {as_float(metrics.get('totalEquity')):,.2f}, "
                f"com resultado de R$ {as_float(metrics.get('pnl')):,.2f} ({as_float(metrics.get('pnlPct')):.2f}%). "
                f"A maior classe e {(portfolio_snapshot.get('largest') or {}).get('class', {}).get('name', 'nao classificada')}."
            ),
            dataUsed=["dashboard.metrics", "portfolioSnapshot"],
            confidence="alta",
        ),
        CopilotQuestion(
            id="largest_asset",
            question="Qual ativo pesa mais?",
            category="portfolio",
            answer=largest_answer,
            dataUsed=["portfolio.positions.weight"],
            confidence="alta" if largest else "baixa",
        ),
    ]


def answer_question(db: Session, user_id: str, question_id: str) -> dict:
    for question in build_copilot_questions(db, user_id):
        if question.id == question_id:
            return {
                "id": question.id,
                "question": question.question,
                "answer": question.answer,
                "category": question.category,
                "dataUsed": question.dataUsed,
                "confidence": question.confidence,
            }
    return {
        "id": question_id,
        "question": "Pergunta nao cadastrada",
        "answer": "O Alpha Copilot ainda nao possui resposta estruturada para essa pergunta.",
        "category": "desconhecida",
        "dataUsed": [],
        "confidence": "baixa",
    }


def copilot_status() -> dict:
    settings = get_settings()
    has_key = bool(settings.alpha_copilot_api_key or settings.openai_api_key)
    enabled = bool(settings.alpha_copilot_ai_enabled and has_key)
    return {
        "status": "ai_enabled" if enabled else "deterministic_fallback",
        "aiEnabled": enabled,
        "provider": settings.alpha_copilot_provider,
        "model": settings.alpha_copilot_model if enabled else "",
        "rules": COPILOT_RULES,
        "warnings": [] if enabled else ["IA externa nao configurada; usando resposta deterministica com os mesmos dados internos."],
    }


def ask_copilot(db: Session, user_id: str, message: str, conversation_id: str | None = None) -> dict:
    normalized_message = " ".join(message.strip().split())
    context = build_copilot_context(db, user_id)
    settings = get_settings()
    warnings: list[str] = []
    provider_payload: dict[str, Any] | None = None

    if _ai_available(settings):
        try:
            provider_payload = _ask_llm(settings, normalized_message, context)
        except Exception as exc:  # pragma: no cover - exact provider failures vary.
            warnings.append(f"Provider de IA indisponivel: {str(exc)[:160]}. Usei fallback interno.")

    if provider_payload:
        response = _response_from_provider(normalized_message, context, provider_payload, warnings)
    else:
        response = _deterministic_response(normalized_message, context, warnings)

    return to_dict(response)


def build_copilot_context(db: Session, user_id: str) -> dict:
    dashboard = get_dashboard(db, user_id)
    positions = sorted(get_positions(db, user_id), key=lambda item: as_float(item.get("weight")), reverse=True)
    portfolio_snapshot = dashboard.get("portfolioSnapshot") or build_user_portfolio_snapshot(db, user_id)
    goals = build_goals(db, user_id)
    wealth_score = build_wealth_progress_score(db, user_id)
    guardian = build_guardian_report(db, user_id)
    confidence = build_data_confidence(db, user_id)
    strategy = build_strategy_report(db, user_id)
    stress = build_stress_test_report(db, user_id)
    economic = build_economic_readings(db, user_id)
    metrics = dashboard["metrics"]
    summary = {
        "totalEquity": as_float(metrics.get("totalEquity")),
        "investedValue": as_float(metrics.get("investedValue")),
        "pnl": as_float(metrics.get("pnl")),
        "pnlPct": as_float(metrics.get("pnlPct")),
        "projectedPassiveIncome": as_float(metrics.get("projectedPassiveIncome")),
        "projectedProceedsIncome": as_float(metrics.get("projectedProceedsIncome")),
        "projectedFixedIncome": as_float(metrics.get("projectedFixedIncome")),
        "dividendsYear": as_float(metrics.get("dividendsYear")),
        "externalEquity": as_float(metrics.get("externalEquity")),
    }
    context = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "summary": summary,
        "portfolioSnapshot": portfolio_snapshot,
        "positions": [_position_context(item) for item in positions[:15]],
        "goals": [asdict(item) for item in goals[:6]],
        "wealthProgressScore": asdict(wealth_score),
        "guardian": asdict(guardian),
        "dataConfidence": [asdict(item) for item in confidence],
        "strategyReport": {
            "status": strategy.status,
            "headline": strategy.headline,
            "primaryStrategy": strategy.primaryStrategy,
            "primaryScore": strategy.primaryScore,
            "currentAllocation": strategy.currentAllocation,
            "metrics": strategy.metrics,
        },
        "stressTest": {
            "status": stress.status,
            "headline": stress.headline,
            "baseEquity": stress.baseEquity,
            "worstScenarioId": stress.worstScenarioId,
            "worstImpactValue": stress.worstImpactValue,
            "worstImpactPct": stress.worstImpactPct,
            "resilienceScore": stress.resilienceScore,
            "riskLevel": stress.riskLevel,
            "exposureBreakdown": stress.exposureBreakdown,
            "scenarios": [asdict(item) for item in stress.scenarios[:5]],
        },
        "economicReadings": [asdict(item) for item in economic[:5]],
    }
    context["sources"] = _build_sources(context)
    return context


def _position_context(item: dict) -> dict:
    return {
        "ticker": item.get("ticker"),
        "name": item.get("name"),
        "assetClass": item.get("class"),
        "sector": item.get("sector"),
        "quantity": as_float(item.get("quantity"), 6),
        "currentValue": as_float(item.get("currentValue")),
        "investedValue": as_float(item.get("investedValue")),
        "pnl": as_float(item.get("pnl")),
        "returnPct": as_float(item.get("returnPct")),
        "weight": as_float(item.get("weight")),
    }


def _build_sources(context: dict) -> list[dict]:
    sources: list[dict] = []

    def add(title: str, source: str, data_path: str, excerpt: str, value: str = "", confidence: str = "media") -> None:
        sources.append(
            {
                "id": f"S{len(sources) + 1}",
                "title": title,
                "source": source,
                "dataPath": data_path,
                "confidence": confidence,
                "excerpt": excerpt,
                "value": value,
            }
        )

    summary = context["summary"]
    snapshot = context["portfolioSnapshot"]
    add(
        "Resumo consolidado da carteira",
        "dashboard.metrics",
        "summary",
        f"Patrimonio R$ {summary['totalEquity']:,.2f}, investido R$ {summary['investedValue']:,.2f}, P/L R$ {summary['pnl']:,.2f} ({summary['pnlPct']:.2f}%).",
        value=json.dumps(summary, ensure_ascii=False),
        confidence="alta",
    )
    largest = snapshot.get("largest") or {}
    exposures = snapshot.get("exposures") or {}
    add(
        "Fotografia patrimonial unica",
        "portfolio_aggregation_engine",
        "portfolioSnapshot",
        (
            f"Maior classe: {(largest.get('class') or {}).get('name', 'nao classificada')} "
            f"({as_float((largest.get('class') or {}).get('weight')):.2f}%). "
            f"Renda fixa {as_float(exposures.get('fixedIncomePct')):.2f}%, cripto {as_float(exposures.get('cryptoPct')):.2f}% e global {as_float(exposures.get('globalPct')):.2f}%."
        ),
        value=json.dumps(snapshot, ensure_ascii=False),
        confidence="alta",
    )
    if context["positions"]:
        top = context["positions"][0]
        add(
            "Maior posicao da carteira",
            "portfolio.positions",
            "positions[0]",
            f"{top['ticker']} pesa {top['weight']:.2f}% e vale R$ {top['currentValue']:,.2f}.",
            value=json.dumps(top, ensure_ascii=False),
            confidence="alta",
        )
    passive_goal = next((item for item in context["goals"] if item["id"] == "passive_income"), None)
    if passive_goal:
        add(
            "Meta de renda passiva",
            "goal_engine.passive_income",
            "goals.passive_income",
            f"Progresso {passive_goal['progressPct']:.2f}%, faltam R$ {passive_goal['remainingValue']:,.2f} para a renda mensal alvo.",
            value=json.dumps(passive_goal, ensure_ascii=False),
            confidence=passive_goal.get("confidence", "media"),
        )
    score = context["wealthProgressScore"]
    add(
        "Wealth Progress Score",
        "wealth_progress_score",
        "wealthProgressScore",
        f"Score {score['score']:.0f}/100. {score['headline']}",
        value=json.dumps({"score": score["score"], "factors": score["factors"]}, ensure_ascii=False),
        confidence="media",
    )
    guardian = context["guardian"]
    add(
        "Guardian 2.0",
        "guardian",
        "guardian",
        f"{guardian['headline']} Total de itens: {guardian['summary']['total']}.",
        value=json.dumps({"summary": guardian["summary"], "items": guardian["items"][:5]}, ensure_ascii=False),
        confidence="media",
    )
    strategy = context["strategyReport"]
    add(
        "Strategy Engine 2.0",
        "strategy_engine",
        "strategyReport",
        f"Perfil dominante {strategy['primaryStrategy']} com score {strategy['primaryScore']:.0f}/100.",
        value=json.dumps(strategy, ensure_ascii=False),
        confidence="media",
    )
    stress = context["stressTest"]
    add(
        "Scenario & Stress Test",
        "scenario_engine",
        "stressTest",
        f"Pior cenario {stress['worstScenarioId']}, impacto {stress['worstImpactPct']:.2f}% e score de resiliencia {stress['resilienceScore']:.0f}/100.",
        value=json.dumps(stress, ensure_ascii=False),
        confidence="media",
    )
    if context["economicReadings"]:
        add(
            "Leitura macroeconomica",
            "economic_engine",
            "economicReadings",
            " | ".join(item["reading"] for item in context["economicReadings"][:2]),
            value=json.dumps(context["economicReadings"][:3], ensure_ascii=False),
            confidence="media",
        )
    add(
        "Confianca dos dados",
        "data_confidence_engine",
        "dataConfidence",
        "; ".join(f"{item['area']}: {item['confidenceScore']:.0f}/100" for item in context["dataConfidence"][:5]),
        value=json.dumps(context["dataConfidence"], ensure_ascii=False),
        confidence="alta",
    )
    return sources


def _ai_available(settings) -> bool:
    if not settings.alpha_copilot_ai_enabled:
        return False
    if settings.alpha_copilot_provider.lower() != "openai":
        return False
    return bool(settings.alpha_copilot_api_key or settings.openai_api_key)


def _ask_llm(settings, message: str, context: dict) -> dict:
    api_key = settings.alpha_copilot_api_key or settings.openai_api_key
    base_url = settings.openai_base_url.rstrip("/")
    context_payload = _context_for_prompt(context, settings.alpha_copilot_max_context_chars)
    system = (
        "Voce e o Alpha Copilot do Carteira Alpha 360. "
        "Responda em portugues do Brasil, de forma humana, clara e objetiva. "
        "Use somente o CONTEXTO_INTERNO. Se faltar dado, diga que falta dado. "
        "Nunca prometa rentabilidade, nunca diga que algo vai subir, nunca de ordem direta de compra ou venda. "
        "Toda conclusao factual deve citar fontes internas no formato [S1], [S2]. "
        "Retorne JSON valido com as chaves: answer, confidence, citations, followUps, warnings."
    )
    user = {
        "pergunta": message,
        "regras": COPILOT_RULES,
        "contexto_interno": context_payload,
    }
    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": settings.alpha_copilot_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "temperature": 0.15,
            "response_format": {"type": "json_object"},
        },
        timeout=settings.alpha_copilot_timeout_seconds,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{response.status_code} ao chamar provider de IA")
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return parsed if isinstance(parsed, dict) else {}


def _context_for_prompt(context: dict, max_chars: int) -> dict:
    prompt_context = {
        "generatedAt": context["generatedAt"],
        "summary": context["summary"],
        "portfolioSnapshot": context["portfolioSnapshot"],
        "positions": context["positions"],
        "goals": context["goals"],
        "wealthProgressScore": context["wealthProgressScore"],
        "guardian": context["guardian"],
        "strategyReport": context["strategyReport"],
        "stressTest": context["stressTest"],
        "economicReadings": context["economicReadings"],
        "dataConfidence": context["dataConfidence"],
        "sources": context["sources"],
    }
    serialized = json.dumps(prompt_context, ensure_ascii=False)
    if len(serialized) <= max_chars:
        return prompt_context
    reduced = {
        **prompt_context,
        "positions": prompt_context["positions"][:8],
        "guardian": {**prompt_context["guardian"], "items": prompt_context["guardian"]["items"][:4]},
        "stressTest": {**prompt_context["stressTest"], "scenarios": prompt_context["stressTest"]["scenarios"][:3]},
    }
    serialized = json.dumps(reduced, ensure_ascii=False)
    if len(serialized) <= max_chars:
        return reduced
    return {
        "summary": context["summary"],
        "positions": context["positions"][:5],
        "sources": context["sources"],
        "truncated": True,
    }


def _response_from_provider(message: str, context: dict, payload: dict, warnings: list[str]) -> CopilotChatResponse:
    citations = _select_citations(context, payload.get("citations") or [])
    if not citations:
        citations = _select_citations(context, ["S1", "S4", "S7"])
    answer = str(payload.get("answer") or "").strip()
    if not answer:
        return _deterministic_response(message, context, warnings + ["Provider de IA retornou resposta vazia."])
    return CopilotChatResponse(
        id=uuid.uuid4().hex,
        question=message,
        answer=_guardrail_text(answer),
        confidence=_normalize_confidence(payload.get("confidence"), citations),
        mode="ai",
        provider="openai",
        citations=citations,
        followUps=_safe_string_list(payload.get("followUps"))[:4],
        warnings=warnings + _safe_string_list(payload.get("warnings"))[:4],
        dataUsed=sorted({item.dataPath for item in citations}),
    )


def _deterministic_response(message: str, context: dict, warnings: list[str]) -> CopilotChatResponse:
    text = message.lower()
    summary = context["summary"]
    citations = _select_citations(context, ["S1", "S3", "S4", "S5", "S7", "S9"])
    if any(term in text for term in ["liberdade", "aposent", "renda passiva", "meta"]):
        citations = _select_citations(context, ["S1", "S2", "S4", "S5", "S10"])
        passive_goal = next((item for item in context["goals"] if item.get("id") == "passive_income"), None)
        current_income = as_float(summary.get("projectedPassiveIncome"))
        if passive_goal:
            target_income = as_float(passive_goal.get("targetValue"))
            missing_income = as_float(passive_goal.get("remainingValue"))
            progress = as_float(passive_goal.get("progressPct"))
            months = passive_goal.get("estimatedMonths")
            months_text = f" O prazo estimado, pelas premissas salvas, e de aproximadamente {months} meses." if months is not None else ""
            assumptions = " ".join(str(item) for item in passive_goal.get("assumptions", [])[:2])
            answer = (
                f"Michel, hoje sua renda passiva mensal projetada esta em R$ {current_income:,.2f} [S1]. "
                f"Sua meta cadastrada esta em R$ {target_income:,.2f} por mes; portanto faltam R$ {missing_income:,.2f} mensais para chegar nela [S3]. "
                f"Isso representa {progress:.2f}% da meta atual [S3].{months_text} "
                f"As premissas usadas pelo sistema sao: {assumptions} [S3]."
            )
        else:
            answer = (
                f"Michel, hoje sua renda passiva mensal projetada esta em R$ {current_income:,.2f} [S1]. "
                "Ainda nao encontrei uma meta de renda passiva cadastrada para calcular quanto falta [S3]."
            )
    elif any(term in text for term in ["risco", "stress", "crise", "queda", "selic", "dolar", "cripto"]):
        citations = _select_citations(context, ["S2", "S5", "S7", "S9"])
        stress = context["stressTest"]
        answer = (
            f"O principal teste de estresse hoje e {stress['worstScenarioId']}, com impacto estimado de {stress['worstImpactPct']:.2f}% [S7]. "
            f"O score de resiliencia esta em {stress['resilienceScore']:.0f}/100 [S7]. "
            "Se o Guardian tiver itens abertos, eles devem ser lidos como pontos de acompanhamento antes de aumentar risco [S5]."
        )
    elif any(term in text for term in ["score", "nota", "caiu", "subiu"]):
        citations = _select_citations(context, ["S4", "S5", "S9"])
        score = context["wealthProgressScore"]
        weak = [item for item in score.get("factors", []) if as_float(item.get("score")) < 60]
        weak_text = ", ".join(item.get("name", "") for item in weak[:3]) or "nenhum fator critico no recorte atual"
        answer = (
            f"O Wealth Progress Score esta em {score['score']:.0f}/100 [S4]. "
            f"Os fatores que mais merecem acompanhamento agora sao: {weak_text} [S4]. "
            "Tambem vale conferir o Guardian, porque ele traduz esses pontos em fila operacional de acompanhamento [S5]."
        )
    elif any(term in text for term in ["ativo", "pesa", "maior", "concentr"]):
        citations = _select_citations(context, ["S1", "S2", "S3", "S6"])
        top = ((context.get("portfolioSnapshot") or {}).get("largest") or {}).get("asset") or (context["positions"][0] if context["positions"] else None)
        if top:
            answer = (
                f"O ativo de maior peso hoje e {top.get('name')}, com {as_float(top.get('weight')):.2f}% da carteira e valor atual de R$ {as_float(top.get('value') or top.get('currentValue')):,.2f} [S2]. "
                "Esse dado serve para acompanhar concentracao e impacto de eventos nesse ativo [S6]."
            )
        else:
            answer = "Ainda nao ha posicoes suficientes para apontar o ativo de maior peso [S1]."
    elif any(term in text for term in ["estrategia", "perfil", "barsi", "buffett", "bogle", "global"]):
        citations = _select_citations(context, ["S6", "S1", "S9"])
        strategy = context["strategyReport"]
        answer = (
            f"O Strategy Engine aponta perfil dominante {strategy['primaryStrategy']} com aderencia de {strategy['primaryScore']:.0f}/100 [S6]. "
            "Isso mostra compatibilidade da carteira com estilos patrimoniais, mas nao transforma o resultado em ordem automatica de compra ou venda [S6]."
        )
    else:
        snapshot = context.get("portfolioSnapshot") or {}
        largest = snapshot.get("largest") or {}
        exposures = snapshot.get("exposures") or {}
        answer = (
            f"Com os dados internos, sua carteira esta em R$ {summary['totalEquity']:,.2f}, com P/L de R$ {summary['pnl']:,.2f} ({summary['pnlPct']:.2f}%) [S1]. "
            f"A maior classe e {(largest.get('class') or {}).get('name', 'nao classificada')} ({as_float((largest.get('class') or {}).get('weight')):.2f}%), "
            f"com renda fixa em {as_float(exposures.get('fixedIncomePct')):.2f}%, cripto em {as_float(exposures.get('cryptoPct')):.2f}% e exposicao global em {as_float(exposures.get('globalPct')):.2f}% [S2]. "
            "O Alpha cruza metas, Guardian, estrategia e stress test para explicar a situacao sem inventar informacao fora do sistema [S5] [S6] [S8]."
        )
    return CopilotChatResponse(
        id=uuid.uuid4().hex,
        question=message,
        answer=_guardrail_text(answer),
        confidence=_normalize_confidence("media", citations),
        mode="deterministic",
        provider="internal",
        citations=citations,
        followUps=[
            "Quer que eu explique o risco atual da carteira?",
            "Quer que eu mostre o que mais pesa no seu patrimonio?",
            "Quer que eu conecte isso com sua meta de renda passiva?",
        ],
        warnings=warnings + ["Resposta gerada sem LLM externo; usei apenas os dados internos consolidados."],
        dataUsed=sorted({item.dataPath for item in citations}),
    )


def _select_citations(context: dict, requested: list[Any]) -> list[CopilotCitation]:
    wanted = {str(item).strip().upper() for item in requested if str(item).strip()}
    source_map = {item["id"].upper(): item for item in context["sources"]}
    selected = []
    for source_id in wanted:
        if source_id in source_map:
            selected.append(_citation_from_source(source_map[source_id]))
    return selected


def _citation_from_source(source: dict) -> CopilotCitation:
    return CopilotCitation(
        id=source["id"],
        title=source["title"],
        source=source["source"],
        dataPath=source["dataPath"],
        confidence=source["confidence"],
        excerpt=source["excerpt"],
        value=source.get("value", ""),
    )


def _guardrail_text(answer: str) -> str:
    replacements = {
        "compre agora": "estude este ativo com prioridade",
        "venda agora": "revise a tese e o peso do ativo",
        "vai subir": "pode ter potencial, mas precisa de validacao",
        "sem risco": "com risco a ser acompanhado",
        "garantido": "estimado",
    }
    sanitized = answer
    for source, target in replacements.items():
        sanitized = sanitized.replace(source, target).replace(source.capitalize(), target.capitalize())
    return sanitized


def _safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_confidence(value: Any, citations: list[CopilotCitation]) -> str:
    raw = str(value or "").lower()
    if raw in {"alta", "media", "baixa"}:
        return raw
    if len(citations) >= 4:
        return "media"
    if len(citations) >= 2:
        return "media"
    return "baixa"
