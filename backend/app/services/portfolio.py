from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.engines.financial_projection_engine import FinancialProjectionEngine
from app.models import Asset, Dividend, MarketSnapshot, Transaction
from app.services.asset_taxonomy import classify_position
from app.services.fixed_income import accrue_cdi_lots, fetch_cdi_daily_rates, is_fixed_income_class, parse_cdi_percent
from app.services.income import add_income_to_breakdown, empty_income_breakdown
from app.services.market_data.v2.contracts import DATA_TYPE_PRICE_HISTORY, MarketDataRequest
from app.services.market_data.v2.engine import MarketDataEngine
from app.services.portfolio_aggregation import build_portfolio_snapshot
from app.services.trading_desk_integration import get_trading_desk_summary

PRICE_HISTORY_PRIORITY = {
    "crypto": ["coingecko", "coinmarketcap"],
    "default": ["yahoo_finance", "dados_mercado", "fmp", "twelvedata"],
}


def as_float(value: Decimal | float | int | None, digits: int = 2) -> float:
    if value is None:
        return 0.0
    return round(float(value), digits)


def _month_key(day: date) -> str:
    return f"{day.year}-{day.month:02d}"


def get_positions(db: Session, user_id: str) -> list[dict]:
    transactions = (
        db.execute(
            select(Transaction)
            .options(joinedload(Transaction.asset).joinedload(Asset.snapshot))
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.date.asc(), Transaction.created_at.asc())
        )
        .scalars()
        .all()
    )
    dividends = (
        db.execute(
            select(Dividend)
            .options(joinedload(Dividend.asset))
            .where(Dividend.user_id == user_id)
            .order_by(Dividend.date.asc())
        )
        .scalars()
        .all()
    )

    states: dict[str, dict] = {}
    for tx in transactions:
        state = states.setdefault(
            tx.asset_id,
            {
                "asset": tx.asset,
                "quantity": Decimal("0"),
                "cost": Decimal("0"),
                "transactions": 0,
                "fees": Decimal("0"),
                "fixed_lots": [],
            },
        )
        qty = Decimal(tx.quantity)
        gross = Decimal(tx.quantity) * Decimal(tx.price)
        fees = Decimal(tx.fees or 0)
        if tx.type == "buy":
            state["quantity"] += qty
            state["cost"] += gross + fees
            if is_fixed_income_class(tx.asset.asset_class if tx.asset else ""):
                state["fixed_lots"].append({"date": tx.date, "amount": gross + fees})
        elif tx.type == "sell" and state["quantity"] > 0:
            avg_cost = state["cost"] / state["quantity"]
            sell_qty = min(qty, state["quantity"])
            sold_cost = avg_cost * sell_qty
            state["quantity"] -= sell_qty
            state["cost"] -= avg_cost * sell_qty
            if state["fixed_lots"]:
                _reduce_fixed_income_lots(state["fixed_lots"], sold_cost)
        state["transactions"] += 1
        state["fees"] += fees

    proceeds_by_asset: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    proceeds_last_12m: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    today = date.today()
    cutoff = date(today.year - 1, today.month, min(today.day, 28))
    for dividend in dividends:
        amount = Decimal(dividend.total_amount)
        asset_class = dividend.asset.asset_class if dividend.asset else ""
        proceeds_by_asset[dividend.asset_id] += amount
        if dividend.date >= cutoff:
            proceeds_last_12m[dividend.asset_id] += amount

    fixed_lot_dates = [
        lot["date"]
        for state in states.values()
        for lot in state.get("fixed_lots", [])
        if lot.get("date")
    ]
    cdi_rates = []
    if fixed_lot_dates:
        try:
            cdi_rates = fetch_cdi_daily_rates(min(fixed_lot_dates), today)
        except Exception:
            cdi_rates = []

    total_current = Decimal("0")
    rows: list[dict] = []
    for asset_id, state in states.items():
        qty = state["quantity"]
        if qty <= 0:
            continue
        asset: Asset = state["asset"]
        snapshot: MarketSnapshot | None = asset.snapshot
        price = Decimal(snapshot.price if snapshot and snapshot.price else asset.last_price or 0)
        invested_value = state["cost"]
        fixed_income_info = None
        if is_fixed_income_class(asset.asset_class):
            cdi_percent = parse_cdi_percent(asset.sector, asset.segment, asset.name, asset.ticker)
            fixed_income_info = accrue_cdi_lots(
                state.get("fixed_lots") or [{"date": today, "amount": invested_value}],
                cdi_percent=cdi_percent,
                end_date=today,
                rates=cdi_rates,
            )
            current_value = Decimal(str(fixed_income_info["currentValue"]))
            price = current_value / qty if qty else Decimal("0")
        else:
            current_value = qty * price
        total_current += current_value
        avg_price = invested_value / qty if qty else Decimal("0")
        pnl = current_value - invested_value
        return_pct = (pnl / invested_value * Decimal("100")) if invested_value else Decimal("0")
        dy_on_avg = (
            proceeds_last_12m[asset_id] / invested_value * Decimal("100") if invested_value else Decimal("0")
        )
        row = {
            "assetId": asset_id,
            "ticker": asset.ticker,
            "name": asset.name,
            "class": asset.asset_class,
            "sector": asset.sector,
            "segment": asset.segment,
            "quantity": as_float(qty, 4),
            "averagePrice": as_float(avg_price),
            "currentPrice": as_float(price),
            "investedValue": as_float(invested_value),
            "currentValue": as_float(current_value),
            "pnl": as_float(pnl),
            "returnPct": as_float(return_pct),
            "dividendYieldOnAvg": as_float(dy_on_avg),
            "dividendsReceived": as_float(proceeds_by_asset[asset_id]),
            "transactions": state["transactions"],
            "fees": as_float(state["fees"]),
            "weight": 0.0,
        }
        if fixed_income_info:
            row["fixedIncome"] = fixed_income_info
        rows.append(row)

    for row in rows:
        row["weight"] = as_float(Decimal(str(row["currentValue"])) / total_current * Decimal("100") if total_current else 0)

    return sorted(rows, key=lambda item: item["currentValue"], reverse=True)


def get_positions_with_month_performance(db: Session, user_id: str) -> list[dict]:
    positions = get_positions(db, user_id)
    if not positions:
        return positions

    today = date.today()
    performance_start = _month_performance_start(today)
    rolling_30_start = today - timedelta(days=30)
    engine = MarketDataEngine(db=db)

    for position in positions:
        position["monthStartDate"] = performance_start.isoformat()
        position["monthStartPrice"] = position.get("currentPrice") or 0
        position["monthStartValue"] = position.get("currentValue") or 0
        position["monthPnl"] = 0.0
        position["monthReturnPct"] = 0.0
        position["monthPerformanceSource"] = "not_applicable"
        position["rolling30StartDate"] = rolling_30_start.isoformat()
        position["rolling30StartPrice"] = position.get("currentPrice") or 0
        position["rolling30StartValue"] = position.get("currentValue") or 0
        position["rolling30Pnl"] = 0.0
        position["rolling30ReturnPct"] = 0.0
        position["rolling30PerformanceSource"] = "not_applicable"

        asset = db.get(Asset, position.get("assetId")) if position.get("assetId") else None
        taxonomy = classify_position(position, asset)
        if taxonomy.is_fixed_income or asset is None:
            continue

        try:
            request = MarketDataRequest(
                symbol=asset.ticker,
                asset_id=asset.id,
                provider_symbol=asset.provider_symbol or asset.ticker,
                market=asset.market or ("Crypto" if taxonomy.is_crypto else "B3"),
                asset_class=asset.asset_class,
                currency=asset.currency or "BRL",
                start_date=min(performance_start, rolling_30_start) - timedelta(days=10),
                end_date=today,
                interval="1day",
            )
            record, prices = _first_price_history(engine, request, crypto=taxonomy.is_crypto)
            current_price = as_float(position.get("currentPrice"), 6)
            start_price = _month_start_price(prices, performance_start, current_price)
            rolling_30_start_price = _price_at_or_before(prices, rolling_30_start, current_price)
            quantity = as_float(position.get("quantity"), 6)
            start_value = quantity * start_price
            rolling_30_start_value = quantity * rolling_30_start_price
            current_value = as_float(position.get("currentValue"))
            month_pnl = current_value - start_value
            rolling_30_pnl = current_value - rolling_30_start_value
            position["monthStartPrice"] = as_float(start_price, 6)
            position["monthStartValue"] = as_float(start_value)
            position["monthPnl"] = as_float(month_pnl)
            position["monthReturnPct"] = as_float(month_pnl / start_value * 100 if start_value else 0.0)
            position["monthPerformanceSource"] = record.provider if record and prices else "fallback_current_price"
            position["rolling30StartPrice"] = as_float(rolling_30_start_price, 6)
            position["rolling30StartValue"] = as_float(rolling_30_start_value)
            position["rolling30Pnl"] = as_float(rolling_30_pnl)
            position["rolling30ReturnPct"] = as_float(
                rolling_30_pnl / rolling_30_start_value * 100 if rolling_30_start_value else 0.0
            )
            position["rolling30PerformanceSource"] = record.provider if record and prices else "fallback_current_price"
        except Exception:
            position["monthPerformanceSource"] = "fallback_current_price"
            position["rolling30PerformanceSource"] = "fallback_current_price"

    try:
        db.commit()
    except Exception:
        db.rollback()
    return sorted(positions, key=lambda item: item["currentValue"], reverse=True)


def _first_price_history(engine: MarketDataEngine, request: MarketDataRequest, *, crypto: bool = False):
    records = engine.collect(DATA_TYPE_PRICE_HISTORY, request, include_mock=False)
    priority = PRICE_HISTORY_PRIORITY["crypto" if crypto else "default"]
    candidates = []
    for record in records:
        provider = (record.provider or "").lower()
        if provider not in priority:
            continue
        prices = _extract_price_rows(record.payload.get("prices") or [])
        if not prices:
            continue
        candidates.append((priority.index(provider), -float(record.quality_score or 0), record, prices))
    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2], candidates[0][3]
    return None, []


def _extract_price_rows(rows: list[dict]) -> list[dict]:
    prices = []
    for row in rows:
        day = _parse_price_date(row.get("date"))
        close = row.get("close", row.get("price"))
        if day is None or close is None:
            continue
        try:
            prices.append({"date": day, "close": float(close)})
        except (TypeError, ValueError):
            continue
    return sorted(prices, key=lambda item: item["date"])


def _parse_price_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _month_start_price(prices: list[dict], month_start: date, fallback: float) -> float:
    for row in prices:
        if row["date"] >= month_start:
            return as_float(row.get("close"), 6)
    before = None
    for row in prices:
        if row["date"] <= month_start:
            before = row
    return as_float((before or {}).get("close"), 6) or fallback


def _price_at_or_before(prices: list[dict], target: date, fallback: float) -> float:
    selected = None
    for row in prices:
        if row["date"] <= target:
            selected = row
        else:
            break
    if selected is None and prices:
        selected = prices[0]
    return as_float((selected or {}).get("close"), 6) or fallback


def _month_performance_start(today: date) -> date:
    return date(today.year, today.month, 1) - timedelta(days=1)


def _reduce_fixed_income_lots(lots: list[dict], amount: Decimal) -> None:
    remaining = Decimal(amount)
    while lots and remaining > 0:
        lot_amount = Decimal(lots[0].get("amount") or 0)
        if lot_amount <= remaining:
            remaining -= lot_amount
            lots.pop(0)
        else:
            lots[0]["amount"] = lot_amount - remaining
            remaining = Decimal("0")


def get_dividend_history(db: Session, user_id: str, months: int = 12) -> list[dict]:
    dividends = db.execute(select(Dividend).where(Dividend.user_id == user_id)).scalars().all()
    grouped: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    today = date.today()
    labels = []
    year = today.year
    month = today.month
    for _ in range(months):
        labels.append(f"{year}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    labels.reverse()
    for dividend in dividends:
        key = _month_key(dividend.date)
        if key in labels:
            grouped[key] += Decimal(dividend.total_amount)
    return [{"month": key, "dividends": as_float(grouped[key]), "proceeds": as_float(grouped[key])} for key in labels]


def get_income_breakdown(db: Session, user_id: str, year: int | None = None, month: int | None = None) -> dict:
    query = select(Dividend).options(joinedload(Dividend.asset)).where(Dividend.user_id == user_id)
    dividends = db.execute(query).scalars().all()
    breakdown = empty_income_breakdown()
    for dividend in dividends:
        if year is not None and dividend.date.year != year:
            continue
        if month is not None and dividend.date.month != month:
            continue
        asset_class = dividend.asset.asset_class if dividend.asset else ""
        add_income_to_breakdown(breakdown, float(dividend.total_amount), dividend.source, asset_class)
    return breakdown


def get_allocations(positions: list[dict], external_accounts: list[dict] | None = None) -> dict:
    return build_portfolio_snapshot(positions, external_accounts=external_accounts)["allocations"]


def get_portfolio_summary(positions: list[dict]) -> dict:
    groups = {
        "stocks": {
            "label": "Acoes",
            "assetCount": 0,
            "quantity": 0.0,
            "investedValue": 0.0,
            "currentValue": 0.0,
            "pnl": 0.0,
            "returnPct": 0.0,
        },
        "crypto": {
            "label": "Cripto",
            "assetCount": 0,
            "quantity": 0.0,
            "investedValue": 0.0,
            "currentValue": 0.0,
            "pnl": 0.0,
            "returnPct": 0.0,
        },
        "fixedIncome": {
            "label": "Renda fixa",
            "assetCount": 0,
            "quantity": 0.0,
            "investedValue": 0.0,
            "currentValue": 0.0,
            "pnl": 0.0,
            "returnPct": 0.0,
        },
        "total": {
            "label": "Consolidado",
            "assetCount": 0,
            "quantity": 0.0,
            "investedValue": 0.0,
            "currentValue": 0.0,
            "pnl": 0.0,
            "returnPct": 0.0,
        },
    }
    for position in positions:
        taxonomy = classify_position(position)
        if taxonomy.is_crypto:
            bucket = "crypto"
        elif taxonomy.is_fixed_income:
            bucket = "fixedIncome"
        elif taxonomy.is_traditional_passive_income:
            bucket = "stocks"
        else:
            bucket = ""
        for key in [bucket, "total"] if bucket else ["total"]:
            groups[key]["assetCount"] += 1
            groups[key]["quantity"] += float(position.get("quantity") or 0)
            groups[key]["investedValue"] += float(position.get("investedValue") or 0)
            groups[key]["currentValue"] += float(position.get("currentValue") or 0)
            groups[key]["pnl"] += float(position.get("pnl") or 0)
        continue
        class_name = str(position.get("class") or "").lower()
        if class_name in {"cripto", "crypto"}:
            bucket = "crypto"
        elif is_fixed_income_class(class_name):
            bucket = "fixedIncome"
        elif class_name in {"acoes", "ações", "fiis", "etfs", "bdrs"}:
            bucket = "stocks"
        else:
            bucket = ""
        for key in [bucket, "total"] if bucket else ["total"]:
            groups[key]["assetCount"] += 1
            groups[key]["quantity"] += float(position.get("quantity") or 0)
            groups[key]["investedValue"] += float(position.get("investedValue") or 0)
            groups[key]["currentValue"] += float(position.get("currentValue") or 0)
            groups[key]["pnl"] += float(position.get("pnl") or 0)

    for group in groups.values():
        invested = group["investedValue"]
        group["quantity"] = round(group["quantity"], 4)
        group["investedValue"] = round(group["investedValue"], 2)
        group["currentValue"] = round(group["currentValue"], 2)
        group["pnl"] = round(group["pnl"], 2)
        group["returnPct"] = round(group["pnl"] / invested * 100, 2) if invested else 0.0

    return {
        **groups,
        "calculation": "current_value_vs_average_cost",
        "periodLabel": "Atual",
    }


def get_portfolio_history(positions: list[dict], months: int = 18, *, external_equity: float = 0.0, external_invested: float = 0.0) -> list[dict]:
    today = date.today()
    labels = []
    year = today.year
    month = today.month
    for _ in range(months):
        labels.append(f"{year}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    labels.reverse()

    total_current = sum(item["currentValue"] for item in positions) + external_equity
    total_invested = sum(item["investedValue"] for item in positions) + external_invested
    rows = []
    for index, label in enumerate(labels, start=1):
        progress = index / len(labels)
        invested = total_invested * (0.35 + 0.65 * progress)
        appreciation = (total_current / total_invested - 1) if total_invested else 0
        wave = 1 + (0.018 if index % 4 == 0 else -0.006 if index % 5 == 0 else 0)
        value = invested * (1 + appreciation * progress) * wave
        rows.append({"month": label, "invested": round(invested, 2), "equity": round(value, 2)})
    if rows:
        rows[-1]["equity"] = round(total_current, 2)
        rows[-1]["invested"] = round(total_invested, 2)
    return rows


def get_dashboard(db: Session, user_id: str) -> dict:
    positions = get_positions(db, user_id)
    portfolio_current = sum(item["currentValue"] for item in positions)
    portfolio_invested = sum(item["investedValue"] for item in positions)
    portfolio_pnl = portfolio_current - portfolio_invested

    trading_desk = get_trading_desk_summary(db=db, user_id=user_id)
    external_accounts: list[dict] = []
    external_current = 0.0
    external_invested = 0.0
    external_pnl = 0.0
    if trading_desk.get("connected"):
        external_current = float(trading_desk["currentBalance"])
        external_invested = float(trading_desk["initialCapital"])
        external_pnl = float(trading_desk["totalPnl"])
        external_accounts.append(
            {
                "ticker": "Trading Desk EV+",
                "name": "Trading Desk EV+",
                "class": "Trading",
                "sector": "Estrategias",
                "currentValue": external_current,
                "investedValue": external_invested,
                "pnl": external_pnl,
                "currency": "BRL",
                "country": "BR",
            }
        )

    total_current = portfolio_current + external_current
    total_invested = portfolio_invested + external_invested
    pnl = portfolio_pnl + external_pnl
    pnl_pct = pnl / total_invested * 100 if total_invested else 0
    assets_by_id = {position["assetId"]: db.get(Asset, position["assetId"]) for position in positions if position.get("assetId")}
    portfolio_snapshot = build_portfolio_snapshot(positions, external_accounts=external_accounts, assets_by_id=assets_by_id)

    today = date.today()
    income_month = get_income_breakdown(db, user_id, today.year, today.month)
    income_year = get_income_breakdown(db, user_id, today.year)
    dividends_month = income_month["total_proceeds"]
    dividends_year = income_year["total_proceeds"]
    projected_proceeds_income = 0.0
    projected_fixed_income = 0.0
    for position in positions:
        asset = db.get(Asset, position["assetId"])
        if asset and asset.asset_class == "Cripto":
            continue
        if asset and is_fixed_income_class(asset.asset_class):
            projected_fixed_income += _project_fixed_income_monthly_income(position)
            continue
        dy = float(asset.snapshot.dividend_yield) if asset and asset.snapshot else 0
        projected_proceeds_income += position["currentValue"] * dy / 100 / 12
    projected_income = projected_proceeds_income + projected_fixed_income

    projection_engine = FinancialProjectionEngine()

    return {
        "metrics": {
            "totalEquity": round(total_current, 2),
            "investedValue": round(total_invested, 2),
            "pnl": round(pnl, 2),
            "pnlPct": round(pnl_pct, 2),
            "dividendsMonth": round(dividends_month, 2),
            "dividendsYear": round(dividends_year, 2),
            "proceedsMonth": round(dividends_month, 2),
            "proceedsYear": round(dividends_year, 2),
            "incomeBreakdownMonth": income_month,
            "incomeBreakdownYear": income_year,
            "projectedPassiveIncome": round(projected_income, 2),
            "projectedProceedsIncome": round(projected_proceeds_income, 2),
            "projectedFixedIncome": round(projected_fixed_income, 2),
            "projectedPassiveIncomeBreakdown": {
                "proceeds": round(projected_proceeds_income, 2),
                "fixedIncome": round(projected_fixed_income, 2),
                "description": "Soma mensal estimada de proventos e renda fixa/CDI. Não inclui valorização de mercado de ações ou cripto.",
            },
            "portfolioEquity": round(portfolio_current, 2),
            "externalEquity": round(external_current, 2),
            "tradingDeskBalance": round(external_current, 2),
            "tradingDeskPnl": round(external_pnl, 2),
            "projection10y": projection_engine.dashboard_projection(
                initial_wealth=total_current,
                monthly_contribution=2500,
                monthly_return_pct=0.8,
                years=10,
            ),
            "projection20y": projection_engine.dashboard_projection(
                initial_wealth=total_current,
                monthly_contribution=2500,
                monthly_return_pct=0.8,
                years=20,
            ),
            "projection30y": projection_engine.dashboard_projection(
                initial_wealth=total_current,
                monthly_contribution=2500,
                monthly_return_pct=0.8,
                years=30,
            ),
        },
        "history": get_portfolio_history(positions, external_equity=external_current, external_invested=external_invested),
        "dividendHistory": get_dividend_history(db, user_id),
        "allocations": portfolio_snapshot["allocations"],
        "portfolioSnapshot": portfolio_snapshot,
        "positions": positions[:6],
        "externalIntegrations": {
            "tradingDesk": trading_desk,
        },
    }


def _project_fixed_income_monthly_income(position: dict) -> float:
    current_value = float(position.get("currentValue") or 0)
    fixed_info = position.get("fixedIncome") or {}
    if current_value <= 0:
        return 0.0
    cdi_percent = float(fixed_info.get("cdiPercent") or 100)
    daily_rate_pct = float(fixed_info.get("dailyRatePct") or 0.041)
    daily_factor = 1 + ((daily_rate_pct / 100) * (cdi_percent / 100))
    monthly_factor = daily_factor**21
    return current_value * (monthly_factor - 1)
