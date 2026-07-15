from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.alpha.event_engine import build_portfolio_events
from app.alpha.insight_engine import build_insights
from app.alpha.timeline_engine import build_timeline
from app.models import Alert
from app.wealth_os.contracts import WealthEventV2, to_dict
from app.wealth_os.guardian_engine import build_guardian_report


SEVERITY_ORDER = {"critical": 0, "warning": 1, "opportunity": 2, "success": 3, "info": 4}
PRIORITY_BY_SEVERITY = {"critical": "alta", "warning": "media", "opportunity": "media", "success": "baixa", "info": "baixa"}


def _priority(severity: str) -> str:
    return PRIORITY_BY_SEVERITY.get(severity, "baixa")


def _parse_time(value: str) -> float:
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0


def _event(
    *,
    event_id: str,
    event_type: str,
    category: str,
    severity: str,
    asset: str | None,
    title: str,
    message: str,
    impact: str,
    recommended_action: str,
    status: str,
    source: str,
    triggered_at: str,
    lifecycle_stage: str,
    confidence: str,
    read_only: bool = True,
    data_used: list[str] | None = None,
) -> WealthEventV2:
    return WealthEventV2(
        id=event_id,
        eventType=event_type,
        category=category,
        severity=severity,
        priority=_priority(severity),
        asset=asset,
        title=title,
        message=message,
        impact=impact,
        recommendedAction=recommended_action,
        status=status,
        source=source,
        triggeredAt=triggered_at,
        lifecycleStage=lifecycle_stage,
        confidence=confidence,
        readOnly=read_only,
        dataUsed=data_used or [],
    )


def _manual_alerts(db: Session, user_id: str) -> list[WealthEventV2]:
    alerts = (
        db.execute(
            select(Alert)
            .options(joinedload(Alert.asset))
            .where(Alert.user_id == user_id)
            .order_by(Alert.triggered_at.desc())
        )
        .scalars()
        .all()
    )
    return [
        _event(
            event_id=alert.id,
            event_type=alert.type,
            category="manual",
            severity=alert.severity,
            asset=alert.asset.ticker if alert.asset else None,
            title=alert.title,
            message=alert.message,
            impact="Alerta cadastrado no monitoramento da carteira.",
            recommended_action="Acompanhar e marcar como lido quando resolvido.",
            status="lido" if alert.is_read else "aberto",
            source="alerts",
            triggered_at=alert.triggered_at.isoformat(),
            lifecycle_stage="manual",
            confidence="alta",
            read_only=False,
            data_used=["alerts"],
        )
        for alert in alerts
    ]


def _alpha_events(db: Session, user_id: str) -> list[WealthEventV2]:
    timeline = build_timeline(build_portfolio_events(db, user_id))
    events: list[WealthEventV2] = []
    for event in timeline:
        if event.gravidade not in {"critical", "warning", "success"}:
            continue
        events.append(
            _event(
                event_id=f"alpha-event-{event.id}",
                event_type=event.tipo,
                category=event.categoria,
                severity=event.gravidade,
                asset=event.ativo,
                title=event.titulo,
                message=event.descricao,
                impact=event.impacto,
                recommended_action=_action_for_alpha_event(event),
                status="lido" if event.status == "lido" else "aberto",
                source=event.origem,
                triggered_at=event.data,
                lifecycle_stage="detectado",
                confidence="media",
                data_used=["alpha.event_engine", "portfolio"],
            )
        )
    return events


def _insight_events(db: Session, user_id: str) -> list[WealthEventV2]:
    timeline = build_timeline(build_portfolio_events(db, user_id))
    insights = build_insights(db, user_id, timeline)
    severity_by_priority = {"alta": "warning", "media": "info", "baixa": "info"}
    events: list[WealthEventV2] = []
    for index, insight in enumerate(insights[:6], start=1):
        events.append(
            _event(
                event_id=f"alpha-insight-v2-{index}-{insight.tipo}-{insight.titulo}".replace(" ", "-").lower(),
                event_type=insight.tipo,
                category="insight",
                severity=severity_by_priority.get(insight.prioridade, "info"),
                asset=None,
                title=insight.titulo,
                message=insight.descricao,
                impact=insight.impacto,
                recommended_action="Usar como contexto antes de qualquer decisao. Insight nao e ordem automatica.",
                status="aberto",
                source="alpha_insight_engine",
                triggered_at=insight.data,
                lifecycle_stage="interpretado",
                confidence="media",
                data_used=["alpha.insight_engine"],
            )
        )
    return events


def _guardian_events(db: Session, user_id: str) -> list[WealthEventV2]:
    report = build_guardian_report(db, user_id)
    return [
        _event(
            event_id=item.id,
            event_type=item.type,
            category=item.category,
            severity=item.severity,
            asset=item.asset,
            title=item.title,
            message=item.message,
            impact=item.impact,
            recommended_action=item.recommendedAction,
            status=item.status,
            source=item.source,
            triggered_at=item.triggeredAt,
            lifecycle_stage="monitoramento",
            confidence=item.confidence,
            data_used=item.dataUsed,
        )
        for item in report.items
    ]


def _action_for_alpha_event(event) -> str:
    if event.tipo in {"concentracao_elevada", "setor_acima_do_limite"}:
        return "Verificar peso atual e estudar rebalanceamento por proximos aportes."
    if event.tipo == "score_diminuiu":
        return "Acompanhar a nota e conferir dados. Queda de score nao significa venda automatica."
    if event.categoria == "renda":
        return "Conferir proventos, JCP ou rendimentos e acompanhar recorrencia."
    if event.categoria == "patrimonio":
        return "Registrar o marco e manter disciplina de risco."
    return "Acompanhar e cruzar com carteira, metas e Guardian antes de agir."


def build_event_stream_v2(db: Session, user_id: str) -> list[WealthEventV2]:
    events = [
        *_manual_alerts(db, user_id),
        *_alpha_events(db, user_id),
        *_insight_events(db, user_id),
        *_guardian_events(db, user_id),
    ]
    deduped: dict[str, WealthEventV2] = {}
    for event in events:
        deduped.setdefault(event.id, event)
    return sorted(
        deduped.values(),
        key=lambda item: (
            SEVERITY_ORDER.get(item.severity, 9),
            -_parse_time(item.triggeredAt),
        ),
    )


def build_event_payload_v2(db: Session, user_id: str) -> dict:
    events = build_event_stream_v2(db, user_id)
    return {
        "summary": {
            "total": len(events),
            "open": sum(1 for event in events if event.status != "lido"),
            "critical": sum(1 for event in events if event.severity == "critical"),
            "warnings": sum(1 for event in events if event.severity == "warning"),
            "alphaEvents": sum(1 for event in events if "alpha" in event.source),
            "guardian": sum(1 for event in events if event.source == "guardian_v2"),
        },
        "alerts": to_dict(events),
        "events": to_dict(events),
    }

