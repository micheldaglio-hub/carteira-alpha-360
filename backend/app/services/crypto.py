from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.alpha.event_engine import record_event
from app.engines.asset_engine import ensure_asset_engine_metadata
from app.models import Alert, AlphaEventModel, Asset, Dividend, MarketSnapshot, TargetAllocation, Transaction
from app.schemas import CryptoTransactionCreate
from app.services.market_data.v2.contracts import MarketDataUnavailable
from app.services.market_data.v2.engine import MarketDataEngine
from app.services.market_data.providers.coinmarketcap import CoinMarketCapProvider
from app.services.portfolio import get_positions


CRYPTO_CATEGORIES = {
    "BTC": "reserva de valor",
    "ETH": "smart contract",
    "SOL": "smart contract",
    "USDT": "stablecoin",
    "USDC": "stablecoin",
    "BNB": "exchange token",
    "XRP": "infraestrutura",
    "ADA": "smart contract",
    "DOGE": "meme coin",
}


def clean_text(value: str | None, fallback: str) -> str:
    text = (value or "").strip()
    return text or fallback


def get_or_create_crypto_asset(db: Session, payload: CryptoTransactionCreate) -> Asset:
    symbol = payload.symbol.upper().strip()
    name = clean_text(payload.name, symbol)
    category = clean_text(payload.category, CRYPTO_CATEGORIES.get(symbol, "outro"))
    currency = payload.currency.upper().strip()
    asset = db.execute(select(Asset).where(Asset.ticker == symbol)).scalar_one_or_none()
    if asset is None:
        asset = Asset(
            ticker=symbol,
            name=name,
            asset_class="Cripto",
            sector="Cripto",
            segment=category,
            currency=currency,
            provider_symbol=symbol,
            last_price=payload.price,
        )
        ensure_asset_engine_metadata(db, asset, force=True)
        db.add(asset)
        db.flush()
        ensure_asset_engine_metadata(db, asset)
        db.add(MarketSnapshot(asset_id=asset.id, price=payload.price, dividend_yield=0, payout=0))
        db.flush()
    else:
        asset.name = name
        asset.asset_class = "Cripto"
        asset.sector = "Cripto"
        asset.segment = category
        asset.currency = currency
        asset.provider_symbol = symbol
        asset.last_price = payload.price
        ensure_asset_engine_metadata(db, asset)
        if asset.snapshot is None:
            db.add(MarketSnapshot(asset_id=asset.id, price=payload.price, dividend_yield=0, payout=0))
            db.flush()
        else:
            asset.snapshot.price = payload.price
    return asset


def sync_crypto_asset(db: Session, asset: Asset) -> bool:
    price = None
    currency = asset.currency or "BRL"
    try:
        quote = MarketDataEngine(db=db).get_quote(
            asset.ticker,
            asset_id=asset.id,
            provider_symbol=asset.provider_symbol or asset.ticker,
            market="Crypto",
            asset_class="Cripto",
            currency=currency,
        )
        if quote.provider != "mock":
            price = quote.payload.get("price")
            currency = quote.currency or currency
    except MarketDataUnavailable:
        price, currency = _fallback_coinmarketcap_quote(asset.ticker, currency)
    if not price:
        price, currency = _fallback_coinmarketcap_quote(asset.ticker, currency)
    if not price:
        return False
    asset.currency = currency
    asset.last_price = Decimal(str(price))
    if asset.snapshot is None:
        db.add(MarketSnapshot(asset_id=asset.id, price=Decimal(str(price)), dividend_yield=0, payout=0))
    else:
        asset.snapshot.price = Decimal(str(price))
    return True


def _fallback_coinmarketcap_quote(ticker: str, currency: str) -> tuple[float | None, str]:
    fallback = CoinMarketCapProvider().get_quote(ticker, convert=currency)
    if fallback is None:
        return None, currency
    return fallback.price, fallback.currency


def sync_user_crypto(db: Session, user_id: str) -> dict:
    positions = [position for position in get_positions(db, user_id) if position["class"] == "Cripto"]
    updated: list[str] = []
    skipped: list[str] = []
    repaired: list[str] = []
    for position in positions:
        asset = db.get(Asset, position["assetId"])
        if asset is None:
            continue
        if sync_crypto_asset(db, asset):
            updated.append(asset.ticker)
        else:
            if restore_suspicious_crypto_mock_price(asset, position):
                repaired.append(asset.ticker)
            skipped.append(asset.ticker)
    db.commit()
    return {"updated": updated, "skipped": skipped, "repaired": repaired}


def restore_suspicious_crypto_mock_price(asset: Asset, position: dict) -> bool:
    """Undo the generic mock quote that can distort crypto portfolios.

    The mock provider returns 25.0 for unknown symbols. That is useful for demo
    screens, but it must never become the persisted market price of a real
    crypto position. When live providers fail, keep the user's average cost as a
    conservative fallback instead of showing a fantasy profit.
    """

    current_price = float(asset.last_price or 0)
    average_price = float(position.get("averagePrice") or 0)
    if average_price <= 0:
        return False
    if asset.ticker.upper() in {"BTC", "ETH", "SOL"}:
        return False
    if not (24.99 <= current_price <= 25.01):
        return False
    restored = Decimal(str(average_price))
    asset.last_price = restored
    if asset.snapshot is None:
        return False
    asset.snapshot.price = restored
    return True


def register_crypto_transaction(db: Session, user_id: str, payload: CryptoTransactionCreate) -> dict:
    asset = get_or_create_crypto_asset(db, payload)
    sync_crypto_asset(db, asset)
    transaction = Transaction(
        user_id=user_id,
        asset_id=asset.id,
        type=payload.type,
        date=payload.date,
        quantity=payload.quantity,
        price=payload.price,
        fees=payload.fees,
        broker=payload.exchange,
        notes=payload.wallet,
    )
    db.add(transaction)
    db.flush()
    is_buy = payload.type == "buy"
    gross_value = float(payload.quantity * payload.price + payload.fees)
    record_event(
        db,
        user_id,
        type="compra_cripto" if is_buy else "venda_cripto",
        category="cripto",
        severity="info",
        title="Compra de cripto registrada" if is_buy else "Venda de cripto registrada",
        description=f"{asset.ticker} teve {'compra' if is_buy else 'venda'} registrada na carteira cripto.",
        impact=f"Movimentacao de {gross_value:,.2f} {asset.currency}.",
        origin=f"crypto.transaction:{transaction.id}",
        asset_id=asset.id,
        occurred_at=datetime.combine(payload.date, datetime.min.time()),
    )
    db.commit()
    return {"id": transaction.id, "message": "Operacao de cripto registrada."}


def crypto_score(position: dict) -> tuple[float, str, str]:
    symbol = position["ticker"]
    category = position["segment"]
    weight = position["cryptoWeight"]
    total_weight = position["totalWeight"]
    category_base = {
        "reserva de valor": 78,
        "smart contract": 68,
        "stablecoin": 74,
        "DeFi": 54,
        "meme coin": 30,
        "infraestrutura": 58,
        "exchange token": 52,
        "outro": 45,
    }.get(category, 45)
    if symbol in {"BTC", "ETH"}:
        category_base += 8
    concentration_penalty = max(0, weight - 35) * 0.7 + max(0, total_weight - 15) * 0.5
    score = max(0, min(100, category_base - concentration_penalty))
    if category == "stablecoin":
        classification = "Stable"
    elif category == "meme coin":
        classification = "Especulativo"
    elif score >= 76:
        classification = "Nucleo"
    elif score >= 60:
        classification = "Moderado"
    elif score >= 42:
        classification = "Alto risco"
    elif score >= 25:
        classification = "Especulativo"
    else:
        classification = "Evitar"
    reason = "Crypto Score considera categoria, concentracao na carteira cripto e peso na carteira total. Nao avalia dividendos."
    return round(score, 2), classification, reason


def get_crypto_dashboard(db: Session, user_id: str) -> dict:
    all_positions = get_positions(db, user_id)
    crypto_positions = [position for position in all_positions if position["class"] == "Cripto"]
    total_portfolio = sum(position["currentValue"] for position in all_positions)
    crypto_total = sum(position["currentValue"] for position in crypto_positions)
    crypto_invested = sum(position["investedValue"] for position in crypto_positions)
    crypto_pnl = crypto_total - crypto_invested

    latest_transactions = {}
    if crypto_positions:
        asset_ids = [position["assetId"] for position in crypto_positions]
        transactions = (
            db.execute(
                select(Transaction)
                .where(Transaction.user_id == user_id, Transaction.asset_id.in_(asset_ids))
                .order_by(Transaction.date.desc(), Transaction.created_at.desc())
            )
            .scalars()
            .all()
        )
        for transaction in transactions:
            latest_transactions.setdefault(transaction.asset_id, transaction)

    rows = []
    for position in crypto_positions:
        asset = db.get(Asset, position["assetId"])
        crypto_weight = position["currentValue"] / crypto_total * 100 if crypto_total else 0
        total_weight = position["currentValue"] / total_portfolio * 100 if total_portfolio else 0
        enriched = {**position, "cryptoWeight": round(crypto_weight, 2), "totalWeight": round(total_weight, 2)}
        score, classification, reason = crypto_score(enriched)
        transaction = latest_transactions.get(position["assetId"])
        rows.append(
            {
                **enriched,
                "category": position["segment"],
                "exchange": transaction.broker if transaction else "",
                "wallet": transaction.notes if transaction else "",
                "currency": asset.currency if asset else "BRL",
                "cryptoScore": score,
                "cryptoClassification": classification,
                "cryptoJustification": reason,
            }
        )

    largest = rows[0]["ticker"] if rows else None
    crypto_weight_total = crypto_total / total_portfolio * 100 if total_portfolio else 0
    risk = "alto" if crypto_weight_total >= 25 else "moderado" if crypto_weight_total >= 10 else "controlado"
    return {
        "metrics": {
            "cryptoEquity": round(crypto_total, 2),
            "cryptoInvested": round(crypto_invested, 2),
            "cryptoPnl": round(crypto_pnl, 2),
            "cryptoPnlPct": round(crypto_pnl / crypto_invested * 100, 2) if crypto_invested else 0,
            "cryptoWeightTotal": round(crypto_weight_total, 2),
            "largestCrypto": largest,
            "cryptoRisk": risk,
        },
        "positions": rows,
    }


def delete_crypto_position(db: Session, user_id: str, asset_id: str) -> bool:
    asset = db.get(Asset, asset_id)
    if asset is None or asset.asset_class != "Cripto":
        return False
    db.execute(delete(Transaction).where(Transaction.user_id == user_id, Transaction.asset_id == asset_id))
    db.execute(delete(Dividend).where(Dividend.user_id == user_id, Dividend.asset_id == asset_id))
    db.execute(delete(Alert).where(Alert.user_id == user_id, Alert.asset_id == asset_id))
    db.execute(delete(AlphaEventModel).where(AlphaEventModel.user_id == user_id, AlphaEventModel.asset_id == asset_id))
    db.execute(
        delete(TargetAllocation).where(
            TargetAllocation.user_id == user_id,
            TargetAllocation.level == "asset",
            TargetAllocation.target_key == asset.ticker,
        )
    )
    db.commit()
    return True
