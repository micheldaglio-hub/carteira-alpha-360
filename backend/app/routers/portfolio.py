from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Alert, AlphaEventModel, Asset, Dividend, MarketSnapshot, TargetAllocation, Transaction, User
from app.schemas import DividendCreate, TransactionCreate
from app.alpha.event_engine import record_event
from app.engines.asset_engine import ensure_asset_engine_metadata
from app.services.income import normalize_income_type
from app.services.market_data.sync import sync_asset_market_data, sync_user_assets
from app.services.portfolio_backtest import get_current_portfolio_backtest
from app.services.portfolio import get_allocations, get_portfolio_summary, get_positions, get_positions_with_month_performance


router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def clean_text(value: str | None, fallback: str) -> str:
    text = (value or "").strip()
    return text or fallback


def get_or_create_asset(
    db: Session,
    ticker: str,
    price: Decimal,
    *,
    asset_name: str = "",
    asset_class: str = "Acoes",
    sector: str = "Nao classificado",
    segment: str = "Cadastro manual",
) -> Asset:
    normalized = ticker.upper().strip()
    normalized_name = clean_text(asset_name, normalized)
    normalized_class = clean_text(asset_class, "Acoes")
    normalized_sector = clean_text(sector, "Nao classificado")
    normalized_segment = clean_text(segment, "Cadastro manual")
    asset = db.execute(select(Asset).where(Asset.ticker == normalized)).scalar_one_or_none()
    if asset:
        asset.name = normalized_name
        asset.asset_class = normalized_class
        asset.sector = normalized_sector
        asset.segment = normalized_segment
        asset.last_price = price
        if asset.snapshot:
            asset.snapshot.price = price
        ensure_asset_engine_metadata(db, asset)
        return asset
    asset = Asset(
        ticker=normalized,
        name=normalized_name,
        asset_class=normalized_class,
        sector=normalized_sector,
        segment=normalized_segment,
        last_price=price,
        provider_symbol=normalized,
    )
    ensure_asset_engine_metadata(db, asset, force=True)
    db.add(asset)
    db.flush()
    ensure_asset_engine_metadata(db, asset)
    db.add(MarketSnapshot(asset_id=asset.id, price=price, dividend_yield=0, payout=0))
    db.flush()
    return asset


@router.get("")
def portfolio(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    positions = get_positions_with_month_performance(db, user.id)
    return {
        "positions": positions,
        "allocations": get_allocations(positions),
        "summary": get_portfolio_summary(positions),
        "totals": {
            "investedValue": round(sum(item["investedValue"] for item in positions), 2),
            "currentValue": round(sum(item["currentValue"] for item in positions), 2),
            "pnl": round(sum(item["pnl"] for item in positions), 2),
        },
    }


@router.get("/backtest")
def portfolio_backtest(
    start_date: date = Query(default=date(2025, 1, 1)),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_current_portfolio_backtest(db, user.id, start_date, end_date or date.today())


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = get_or_create_asset(
        db,
        payload.ticker,
        payload.price,
        asset_name=payload.asset_name,
        asset_class=payload.asset_class,
        sector=payload.sector,
        segment=payload.segment,
    )
    sync_asset_market_data(db, asset)
    transaction = Transaction(
        user_id=user.id,
        asset_id=asset.id,
        type=payload.type,
        date=payload.date,
        quantity=payload.quantity,
        price=payload.price,
        fees=payload.fees,
        broker=payload.broker,
        notes=payload.notes,
    )
    db.add(transaction)
    db.flush()
    is_buy = payload.type == "buy"
    gross_value = float(payload.quantity * payload.price + payload.fees)
    record_event(
        db,
        user.id,
        type="compra_realizada" if is_buy else "venda_realizada",
        category="movimentacao",
        severity="info",
        title="Compra registrada" if is_buy else "Venda registrada",
        description=f"{asset.ticker} teve {'compra' if is_buy else 'venda'} registrada na carteira.",
        impact=f"Movimentacao de R$ {gross_value:,.2f}.",
        origin=f"portfolio.transaction:{transaction.id}",
        asset_id=asset.id,
        occurred_at=datetime.combine(payload.date, datetime.min.time()),
    )
    db.commit()
    return {"id": transaction.id, "message": "Movimentacao registrada."}


@router.post("/dividends", status_code=status.HTTP_201_CREATED)
def create_dividend(payload: DividendCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = db.execute(select(Asset).where(Asset.ticker == payload.ticker.upper().strip())).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ativo nao encontrado.")
    dividend = Dividend(
        user_id=user.id,
        asset_id=asset.id,
        date=payload.date,
        amount_per_share=payload.amount_per_share,
        total_amount=payload.total_amount,
        source=payload.source,
    )
    db.add(dividend)
    db.flush()
    income_type = normalize_income_type(payload.source, asset.asset_class)
    record_event(
        db,
        user.id,
        type="novo_dividendo_recebido",
        category="renda",
        severity="success",
        title=f"Novo {income_type.label.lower()} recebido",
        description=f"{asset.ticker} adicionou {income_type.label.lower()} ao fluxo de renda passiva da carteira.",
        impact=f"Entrada de R$ {float(payload.total_amount):,.2f} em proventos.",
        origin=f"portfolio.dividend:{dividend.id}",
        asset_id=asset.id,
        occurred_at=datetime.combine(payload.date, datetime.min.time()),
    )
    db.commit()
    return {"id": dividend.id, "message": f"{income_type.label} registrado como provento."}


@router.post("/sync-market")
def sync_market(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return sync_user_assets(db, user.id)


@router.delete("/positions/{asset_id}")
def delete_position(asset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ativo nao encontrado.")

    transaction_count = (
        db.execute(select(Transaction).where(Transaction.user_id == user.id, Transaction.asset_id == asset_id))
        .scalars()
        .all()
    )
    dividend_count = (
        db.execute(select(Dividend).where(Dividend.user_id == user.id, Dividend.asset_id == asset_id))
        .scalars()
        .all()
    )
    if not transaction_count and not dividend_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posicao nao encontrada para este usuario.")

    db.execute(delete(Transaction).where(Transaction.user_id == user.id, Transaction.asset_id == asset_id))
    db.execute(delete(Dividend).where(Dividend.user_id == user.id, Dividend.asset_id == asset_id))
    db.execute(delete(Alert).where(Alert.user_id == user.id, Alert.asset_id == asset_id))
    db.execute(delete(AlphaEventModel).where(AlphaEventModel.user_id == user.id, AlphaEventModel.asset_id == asset_id))
    db.execute(
        delete(TargetAllocation).where(
            TargetAllocation.user_id == user.id,
            TargetAllocation.level == "asset",
            TargetAllocation.target_key == asset.ticker,
        )
    )
    db.commit()
    return {"ok": True, "message": f"Posicao {asset.ticker} removida da carteira."}
