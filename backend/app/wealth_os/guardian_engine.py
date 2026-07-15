from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.alpha.alpha_score_engine import calculate_alpha_scores_v2
from app.alpha.health_engine import calculate_health
from app.services.alpha_b3_screener import OFFICIAL_TARGET_WEIGHTS
from app.services.portfolio import get_allocations, get_dashboard, get_positions
from app.wealth_os.contracts import GuardianItem, GuardianReport
from app.wealth_os.data_confidence_engine import build_data_confidence
from app.wealth_os.goal_engine import build_goals
from app.wealth_os.utils import as_float
from app.wealth_os.wealth_progress_engine import build_wealth_progress_score


ASSET_REVIEW_THRESHOLD = 42
HEALTH_WARNING_THRESHOLD = 45
HEALTH_BUILDING_THRESHOLD = 60


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _priority(severity: str) -> str:
    if severity == "critical":
        return "alta"
    if severity == "warning":
        return "media"
    return "baixa"


def _item(
    *,
    item_id: str,
    item_type: str,
    category: str,
    severity: str,
    title: str,
    message: str,
    impact: str,
    recommended_action: str,
    asset: str | None = None,
    confidence: str = "media",
    data_used: list[str] | None = None,
) -> GuardianItem:
    return GuardianItem(
        id=item_id,
        type=item_type,
        category=category,
        severity=severity,
        priority=_priority(severity),
        title=title,
        message=message,
        impact=impact,
        recommendedAction=recommended_action,
        asset=asset,
        status="aberto",
        source="guardian_v2",
        triggeredAt=_now(),
        confidence=confidence,
        dataUsed=data_used or [],
    )


def _health_factor_message(name: str, score: float, justification: str) -> str:
    if name == "Renda Passiva":
        return "A renda passiva ainda esta em construcao. Isso e normal no inicio, mas precisa entrar no plano de aportes e registro de proventos."
    if name in {"Dividendos", "Proventos"}:
        return "O Alpha ainda precisa de mais historico de dividendos, JCP e rendimentos para medir melhor a qualidade da renda."
    if name == "Concentracao":
        return "A carteira tem algum peso que merece controle. O caminho mais limpo normalmente e usar proximos aportes para equilibrar."
    if name == "Diversificacao":
        return "Ainda existe espaco para ampliar equilibrio entre ativos, setores, moedas ou classes."
    return justification or f"{name} marcou {score:.0f}/100 e merece acompanhamento."


def _asset_message(row, official: bool) -> str:
    if official:
        return (
            f"{row.ticker} esta na Carteira Recomendada Alpha, mas a leitura operacional atual ficou fraca. "
            "Isso nao cancela a tese; indica que o ativo precisa ser acompanhado com dados atualizados."
        )
    return (
        f"{row.ticker} ficou abaixo da faixa minima do Alpha. "
        "Antes de aumentar exposicao, vale revisar fundamentos, risco, peso e papel do ativo na carteira."
    )


def _asset_impact(row) -> str:
    weakest = sorted(row.scores, key=lambda item: item.nota)[:3]
    if not weakest:
        return "O ativo ficou fraco na leitura agregada."
    return "Pontos que mais pesaram: " + ", ".join(f"{item.nome} {item.nota:.0f}/100" for item in weakest) + "."


def build_guardian_report(db: Session, user_id: str) -> GuardianReport:
    dashboard = get_dashboard(db, user_id)
    positions = get_positions(db, user_id)
    allocations = get_allocations(positions)
    health = calculate_health(db, user_id)
    wealth_score = build_wealth_progress_score(db, user_id)
    goals = build_goals(db, user_id)
    confidence = build_data_confidence(db, user_id)
    items: list[GuardianItem] = []
    metrics = dashboard["metrics"]

    if health.notaGeral < HEALTH_BUILDING_THRESHOLD:
        severity = "warning" if health.notaGeral < HEALTH_WARNING_THRESHOLD else "info"
        items.append(
            _item(
                item_id="guardian-v2-health-general",
                item_type="saude_da_carteira",
                category="carteira",
                severity=severity,
                title="Carteira em construcao patrimonial",
                message=(
                    f"A nota geral esta em {health.notaGeral:.0f}/100. "
                    "Isso indica que o Alpha ainda esta montando uma leitura mais robusta de qualidade, renda, diversificacao e risco."
                ),
                impact="Carteiras recentes oscilam mais na nota porque ainda possuem pouco historico de proventos, aportes e fundamentos completos.",
                recommended_action="Manter a disciplina de registro, atualizar mercado e usar novos aportes para corrigir pesos com calma.",
                confidence="alta",
                data_used=["alpha.health", "portfolio.positions"],
            )
        )

    for factor in [score for score in health.scores if score.nota < HEALTH_WARNING_THRESHOLD][:3]:
        items.append(
            _item(
                item_id=f"guardian-v2-factor-{factor.nome}".replace(" ", "-").lower(),
                item_type="fator_fraco",
                category="saude",
                severity="warning",
                title=f"{factor.nome} merece acompanhamento",
                message=_health_factor_message(factor.nome, factor.nota, factor.justificativa),
                impact=f"Nota atual: {factor.nota:.0f}/100.",
                recommended_action="Usar como direcao para proximos aportes e ajustes graduais, nao como ordem automatica.",
                confidence="media",
                data_used=["alpha.health.scores"],
            )
        )

    largest_asset = max(positions, key=lambda item: as_float(item.get("weight")), default=None)
    if largest_asset and as_float(largest_asset.get("weight")) >= 20:
        weight = as_float(largest_asset.get("weight"))
        items.append(
            _item(
                item_id=f"guardian-v2-concentration-{largest_asset.get('assetId')}",
                item_type="concentracao_individual",
                category="risco",
                severity="critical" if weight >= 30 else "warning",
                title=f"{largest_asset.get('ticker')} concentra a carteira",
                message=f"{largest_asset.get('ticker')} representa {weight:.2f}% do patrimonio monitorado.",
                impact="Quanto maior a concentracao, maior o impacto de uma noticia ruim ou erro de tese.",
                recommended_action="Avaliar se novos aportes devem priorizar outros ativos ou classes para reduzir dependencia.",
                asset=largest_asset.get("ticker"),
                confidence="alta",
                data_used=["portfolio.positions.weight"],
            )
        )

    largest_sector = max(allocations.get("bySector", []), key=lambda item: as_float(item.get("weight")), default=None)
    if largest_sector and as_float(largest_sector.get("weight")) >= 40:
        weight = as_float(largest_sector.get("weight"))
        items.append(
            _item(
                item_id=f"guardian-v2-sector-{largest_sector.get('name')}".replace(" ", "-").lower(),
                item_type="concentracao_setorial",
                category="risco",
                severity="warning",
                title=f"Setor {largest_sector.get('name')} esta dominante",
                message=f"O setor representa {weight:.2f}% do patrimonio monitorado.",
                impact="Setor dominante pode deixar a carteira sensivel a regulacao, ciclo economico ou choque especifico.",
                recommended_action="Comparar com a carteira ideal antes do proximo aporte.",
                confidence="alta",
                data_used=["portfolio.allocations.bySector"],
            )
        )

    alpha_scores = calculate_alpha_scores_v2(db, user_id)
    for row in alpha_scores:
        if row.scoreFinal >= ASSET_REVIEW_THRESHOLD:
            continue
        official = row.ticker in OFFICIAL_TARGET_WEIGHTS
        items.append(
            _item(
                item_id=f"guardian-v2-asset-score-{row.assetId}",
                item_type="ativo_em_revisao",
                category="ativo",
                severity="warning" if official else "critical" if row.scoreFinal < 35 else "warning",
                title=f"{row.ticker} precisa de revisao de tese",
                message=_asset_message(row, official),
                impact=_asset_impact(row),
                recommended_action=(
                    "Atualizar fundamentos e conferir se a tese original continua valida antes de aumentar exposicao."
                    if official
                    else "Revisar tese, fundamentos e peso. Se a leitura continuar fraca, estudar reducao ou substituicao sem automatismo."
                ),
                asset=row.ticker,
                confidence="media",
                data_used=["alpha_score_v2"],
            )
        )

    passive_goal = next((goal for goal in goals if goal.id == "passive_income"), None)
    if passive_goal and passive_goal.progressPct < 20:
        items.append(
            _item(
                item_id="guardian-v2-passive-income-gap",
                item_type="meta_renda_passiva",
                category="metas",
                severity="info",
                title="Renda passiva ainda distante da meta",
                message=f"A renda passiva atual cobre {passive_goal.progressPct:.2f}% da meta cadastrada.",
                impact=f"Faltam R$ {passive_goal.remainingValue:,.2f} por mes para a meta.",
                recommended_action="Usar o Goal Engine e as premissas de aporte para acompanhar o prazo estimado.",
                confidence=passive_goal.confidence,
                data_used=["goal_engine.passive_income", "dashboard.metrics.projectedPassiveIncome"],
            )
        )

    weak_confidence = [item for item in confidence if item.confidenceScore < 60]
    if weak_confidence:
        labels = ", ".join(item.area for item in weak_confidence[:3])
        items.append(
            _item(
                item_id="guardian-v2-data-confidence",
                item_type="confianca_dados",
                category="dados",
                severity="info",
                title="Dados ainda incompletos em areas importantes",
                message=f"As areas com menor confianca agora sao: {labels}.",
                impact="Dados incompletos reduzem a precisao dos scores, metas, oportunidades e alertas.",
                recommended_action="Sincronizar mercado, completar setores/classes e registrar proventos reais.",
                confidence="alta",
                data_used=["data_confidence_engine"],
            )
        )

    if wealth_score.score < 50:
        items.append(
            _item(
                item_id="guardian-v2-wealth-progress",
                item_type="wealth_progress",
                category="wealth_os",
                severity="warning",
                title="Wealth Progress Score pede plano",
                message=wealth_score.headline,
                impact="O score combina metas, diversificacao, concentracao, renda passiva, Saude Alpha e momento da carteira.",
                recommended_action="Priorizar os pontos de atencao do Centro de Comando Patrimonial.",
                confidence="media",
                data_used=["wealth_progress_score"],
            )
        )

    severity_order = {"critical": 0, "warning": 1, "info": 2, "success": 3}
    items = sorted(items, key=lambda item: (severity_order.get(item.severity, 9), item.title))
    summary = {
        "total": len(items),
        "critical": sum(1 for item in items if item.severity == "critical"),
        "warnings": sum(1 for item in items if item.severity == "warning"),
        "info": sum(1 for item in items if item.severity == "info"),
    }
    status = "critico" if summary["critical"] else "atencao" if summary["warnings"] else "estavel"
    headline = (
        "Guardian 2.0 encontrou pontos que merecem acompanhamento."
        if items
        else "Guardian 2.0 nao encontrou pontos urgentes com os dados atuais."
    )
    if as_float(metrics.get("totalEquity")) <= 0:
        headline = "Guardian 2.0 aguardando dados de carteira."
    return GuardianReport(status=status, headline=headline, summary=summary, items=items)
