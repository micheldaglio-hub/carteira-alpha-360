from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.alpha.contracts import AlphaEvent
from app.alpha.utils import date_to_datetime, iso, money, percent
from app.models import Alert, AlphaEventModel, Asset, Dividend, Transaction
from app.services.income import normalize_income_type
from app.services.portfolio import get_allocations, get_dashboard, get_positions
from app.services.scoring import list_scores


def _event_from_model(event: AlphaEventModel) -> AlphaEvent:
    return AlphaEvent(
        id=event.id,
        tipo=event.type,
        categoria=event.category,
        gravidade=event.severity,
        ativo=event.asset.ticker if event.asset else None,
        titulo=event.title,
        descricao=event.description,
        impacto=event.impact,
        data=iso(event.occurred_at),
        status=event.status,
        origem=event.origin,
    )


def _event(
    event_id: str,
    *,
    tipo: str,
    categoria: str,
    gravidade: str,
    ativo: str | None,
    titulo: str,
    descricao: str,
    impacto: str,
    data: datetime,
    status: str = "sintetico",
    origem: str = "alpha_engine",
) -> AlphaEvent:
    return AlphaEvent(
        id=event_id,
        tipo=tipo,
        categoria=categoria,
        gravidade=gravidade,
        ativo=ativo,
        titulo=titulo,
        descricao=descricao,
        impacto=impacto,
        data=iso(data),
        status=status,
        origem=origem,
    )


def record_event(
    db: Session,
    user_id: str,
    *,
    type: str,
    category: str,
    severity: str,
    title: str,
    description: str,
    impact: str,
    origin: str,
    asset_id: str | None = None,
    status: str = "novo",
    occurred_at: datetime | None = None,
) -> AlphaEventModel:
    event = AlphaEventModel(
        user_id=user_id,
        asset_id=asset_id,
        type=type,
        category=category,
        severity=severity,
        title=title,
        description=description,
        impact=impact,
        origin=origin,
        status=status,
        occurred_at=occurred_at or datetime.utcnow(),
    )
    db.add(event)
    return event


def _transaction_events(db: Session, user_id: str, persisted_origins: set[str]) -> list[AlphaEvent]:
    transactions = (
        db.execute(
            select(Transaction)
            .options(joinedload(Transaction.asset))
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        )
        .scalars()
        .all()
    )
    events: list[AlphaEvent] = []
    for tx in transactions:
        origin = f"portfolio.transaction:{tx.id}"
        if origin in persisted_origins:
            continue
        value = float(Decimal(tx.quantity) * Decimal(tx.price) + Decimal(tx.fees or 0))
        is_buy = tx.type == "buy"
        events.append(
            _event(
                f"tx-{tx.id}",
                tipo="compra_realizada" if is_buy else "venda_realizada",
                categoria="movimentacao",
                gravidade="info",
                ativo=tx.asset.ticker,
                titulo="Compra realizada" if is_buy else "Venda realizada",
                descricao=f"{tx.asset.ticker} teve {'compra' if is_buy else 'venda'} registrada na carteira.",
                impacto=f"Movimentacao de {money(value)} com {float(tx.quantity):.4g} unidades.",
                data=date_to_datetime(tx.date),
                origem="portfolio",
            )
        )
    return events


def _dividend_events(db: Session, user_id: str, persisted_origins: set[str]) -> list[AlphaEvent]:
    dividends = (
        db.execute(
            select(Dividend)
            .options(joinedload(Dividend.asset))
            .where(Dividend.user_id == user_id)
            .order_by(Dividend.date.desc(), Dividend.created_at.desc())
        )
        .scalars()
        .all()
    )
    events: list[AlphaEvent] = []
    for dividend in dividends:
        origin = f"portfolio.dividend:{dividend.id}"
        if origin in persisted_origins:
            continue
        total = float(dividend.total_amount)
        income_type = normalize_income_type(dividend.source, dividend.asset.asset_class if dividend.asset else "")
        events.append(
            _event(
                f"div-{dividend.id}",
                tipo="novo_dividendo_recebido",
                categoria="renda",
                gravidade="success",
                ativo=dividend.asset.ticker,
                titulo=f"Novo {income_type.label.lower()} recebido",
                descricao=f"{dividend.asset.ticker} adicionou {income_type.label.lower()} ao fluxo de renda passiva da carteira.",
                impacto=f"Entrada de {money(total)} em proventos.",
                data=date_to_datetime(dividend.date),
                origem="portfolio",
            )
        )
    return events


def _alert_events(db: Session, user_id: str) -> list[AlphaEvent]:
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
            f"alert-{alert.id}",
            tipo=alert.type,
            categoria="alerta",
            gravidade=alert.severity,
            ativo=alert.asset.ticker if alert.asset else None,
            titulo=alert.title,
            descricao=alert.message,
            impacto="Alerta operacional para acompanhamento da carteira.",
            data=alert.triggered_at,
            status="lido" if alert.is_read else "novo",
            origem="alerts",
        )
        for alert in alerts
    ]


def _portfolio_state_events(db: Session, user_id: str) -> list[AlphaEvent]:
    positions = get_positions(db, user_id)
    allocations = get_allocations(positions)
    dashboard = get_dashboard(db, user_id)
    now = datetime.utcnow()
    events: list[AlphaEvent] = []

    for position in positions:
        if position["weight"] >= 20:
            events.append(
                _event(
                    f"concentration-{position['assetId']}",
                    tipo="concentracao_elevada",
                    categoria="risco",
                    gravidade="warning" if position["weight"] < 30 else "critical",
                    ativo=position["ticker"],
                    titulo="Concentracao elevada",
                    descricao=f"{position['ticker']} esta com peso maior que o ideal para uma carteira equilibrada.",
                    impacto=f"Hoje esse ativo representa {percent(position['weight'])} da carteira.",
                    data=now,
                )
            )

    for sector in allocations["bySector"]:
        if sector["weight"] >= 35:
            events.append(
                _event(
                    f"sector-limit-{sector['name'].lower().replace(' ', '-')}",
                    tipo="setor_acima_do_limite",
                    categoria="risco",
                    gravidade="warning" if sector["weight"] < 45 else "critical",
                    ativo=None,
                    titulo="Setor acima do limite",
                    descricao=f"A carteira esta muito exposta ao setor {sector['name']}.",
                    impacto=f"Esse setor representa {percent(sector['weight'])} do patrimonio.",
                    data=now,
                )
            )

    history = dashboard.get("history", [])
    if history:
        current = history[-1]["equity"]
        previous_max = max((row["equity"] for row in history[:-1]), default=0)
        if current >= previous_max and current > 0:
            events.append(
                _event(
                    "record-equity-current",
                    tipo="novo_maior_patrimonio",
                    categoria="patrimonio",
                    gravidade="success",
                    ativo=None,
                    titulo="Novo maior patrimonio",
                    descricao="A carteira esta no maior patrimonio registrado pela serie interna.",
                    impacto=f"Patrimonio atual de {money(float(current))}.",
                    data=now,
                )
            )

    dividends = dashboard.get("dividendHistory", [])
    if dividends:
        current_month = dividends[-1].get("proceeds", dividends[-1]["dividends"])
        previous_max = max((row.get("proceeds", row["dividends"]) for row in dividends[:-1]), default=0)
        if current_month > 0 and current_month >= previous_max:
            events.append(
                _event(
                    "record-dividend-current",
                    tipo="novo_maior_dividendo",
                    categoria="renda",
                    gravidade="success",
                    ativo=None,
                    titulo="Novo maior provento",
                    descricao="O mes atual esta entre os melhores pontos de renda passiva registrados.",
                    impacto=f"Proventos do mes em {money(float(current_month))}.",
                    data=now,
                )
            )

    score_rows = list_scores(db)
    held_ids = {position["assetId"] for position in positions}
    held_scores = [row["scoreFinal"] for row in score_rows if row["assetId"] in held_ids]
    if held_scores:
        avg_score = sum(held_scores) / len(held_scores)
        if avg_score >= 75:
            events.append(
                _event(
                    "score-alpha-strong",
                    tipo="score_aumentou",
                    categoria="score",
                    gravidade="success",
                    ativo=None,
                    titulo="Score Alpha em faixa forte",
                    descricao="Os ativos carregados apresentam leitura agregada positiva pelo motor proprietario.",
                    impacto=f"Score medio dos ativos em {avg_score:.0f}/100.",
                    data=now,
                )
            )
        elif avg_score < 52:
            events.append(
                _event(
                    "score-alpha-watch",
                    tipo="score_diminuiu",
                    categoria="score",
                    gravidade="warning" if avg_score < 45 else "info",
                    ativo=None,
                    titulo="Score Alpha em calibragem",
                    descricao="A carteira ainda esta em fase de construcao e o Alpha esta calibrando a leitura com os dados disponiveis.",
                    impacto=f"Score medio atual dos ativos em {avg_score:.0f}/100. Isso nao significa venda automatica nem invalida a carteira recomendada.",
                    data=now,
                )
            )

    return events


def build_portfolio_events(db: Session, user_id: str) -> list[AlphaEvent]:
    persisted_models = (
        db.execute(
            select(AlphaEventModel)
            .options(joinedload(AlphaEventModel.asset))
            .where(AlphaEventModel.user_id == user_id)
            .order_by(AlphaEventModel.occurred_at.desc())
        )
        .scalars()
        .all()
    )
    persisted = [_event_from_model(event) for event in persisted_models]
    persisted_origins = {event.origin for event in persisted_models}
    events = [
        *persisted,
        *_transaction_events(db, user_id, persisted_origins),
        *_dividend_events(db, user_id, persisted_origins),
        *_alert_events(db, user_id),
        *_portfolio_state_events(db, user_id),
    ]

    deduped: dict[str, AlphaEvent] = {}
    for event in events:
        deduped.setdefault(event.id, event)
    return list(deduped.values())
