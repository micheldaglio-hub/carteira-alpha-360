from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.engines.asset_engine import ensure_asset_engine_metadata
from app.models import Alert, Asset, Dividend, MarketSnapshot, TargetAllocation, Transaction, User


def months_ago(months: int, day: int = 10) -> date:
    today = date.today()
    month_index = today.year * 12 + today.month - 1 - months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(day, 28))


ASSETS = [
    {
        "ticker": "TAEE11",
        "name": "Taesa Units",
        "asset_class": "Acoes",
        "sector": "Energia eletrica",
        "segment": "Transmissao",
        "last_price": 35.16,
        "snapshot": dict(price=35.16, dividend_yield=10.4, payout=78, revenue_growth=5.2, profit_growth=6.8, net_margin=42, roe=21, roic=14, debt_to_ebitda=2.1, historical_appreciation=38, dividend_consistency=91, payment_frequency=8, recurring_profit=84, sector_stability=88, pe_ratio=8.5, pvp=1.7),
    },
    {
        "ticker": "ITSA4",
        "name": "Itausa PN",
        "asset_class": "Acoes",
        "sector": "Holding financeira",
        "segment": "Financeiro",
        "last_price": 10.72,
        "snapshot": dict(price=10.72, dividend_yield=6.3, payout=54, revenue_growth=7.5, profit_growth=9.1, net_margin=28, roe=18, roic=12, debt_to_ebitda=1.0, historical_appreciation=44, dividend_consistency=86, payment_frequency=6, recurring_profit=82, sector_stability=78, pe_ratio=9.8, pvp=1.3),
    },
    {
        "ticker": "PETR4",
        "name": "Petrobras PN",
        "asset_class": "Acoes",
        "sector": "Petroleo e gas",
        "segment": "Integrada",
        "last_price": 38.42,
        "snapshot": dict(price=38.42, dividend_yield=12.1, payout=66, revenue_growth=4.0, profit_growth=3.8, net_margin=22, roe=25, roic=17, debt_to_ebitda=1.4, historical_appreciation=52, dividend_consistency=63, payment_frequency=5, recurring_profit=72, sector_stability=54, pe_ratio=5.2, pvp=1.1),
    },
    {
        "ticker": "HGLG11",
        "name": "CSHG Logistica FII",
        "asset_class": "FIIs",
        "sector": "Logistica",
        "segment": "Galpoes logisticos",
        "last_price": 164.8,
        "snapshot": dict(price=164.8, dividend_yield=8.4, payout=92, revenue_growth=8.0, profit_growth=6.5, net_margin=62, roe=9, roic=8, debt_to_ebitda=0.5, historical_appreciation=25, dividend_consistency=89, payment_frequency=12, recurring_profit=80, sector_stability=82, pe_ratio=13.8, pvp=1.0),
    },
    {
        "ticker": "KNRI11",
        "name": "Kinea Renda Imobiliaria FII",
        "asset_class": "FIIs",
        "sector": "Hibrido",
        "segment": "Lajes e logistica",
        "last_price": 158.9,
        "snapshot": dict(price=158.9, dividend_yield=7.8, payout=88, revenue_growth=6.8, profit_growth=5.9, net_margin=58, roe=8, roic=7, debt_to_ebitda=0.4, historical_appreciation=18, dividend_consistency=85, payment_frequency=12, recurring_profit=77, sector_stability=80, pe_ratio=14.4, pvp=0.98),
    },
    {
        "ticker": "IVVB11",
        "name": "iShares S&P 500 BRL ETF",
        "asset_class": "ETFs",
        "sector": "Exterior",
        "segment": "Indice internacional",
        "last_price": 325.2,
        "snapshot": dict(price=325.2, dividend_yield=1.2, payout=0, revenue_growth=11, profit_growth=12, net_margin=21, roe=19, roic=16, debt_to_ebitda=1.5, historical_appreciation=92, dividend_consistency=42, payment_frequency=0, recurring_profit=88, sector_stability=84, pe_ratio=22, pvp=4.2),
    },
    {
        "ticker": "BOVA11",
        "name": "iShares Ibovespa ETF",
        "asset_class": "ETFs",
        "sector": "Brasil amplo",
        "segment": "Indice local",
        "last_price": 128.4,
        "snapshot": dict(price=128.4, dividend_yield=2.4, payout=0, revenue_growth=6, profit_growth=7, net_margin=16, roe=14, roic=11, debt_to_ebitda=1.7, historical_appreciation=34, dividend_consistency=45, payment_frequency=0, recurring_profit=70, sector_stability=67, pe_ratio=10.8, pvp=1.5),
    },
    {
        "ticker": "WEGE3",
        "name": "WEG ON",
        "asset_class": "Acoes",
        "sector": "Bens industriais",
        "segment": "Motores e equipamentos",
        "last_price": 41.9,
        "snapshot": dict(price=41.9, dividend_yield=1.8, payout=43, revenue_growth=17, profit_growth=20, net_margin=19, roe=27, roic=24, debt_to_ebitda=0.2, historical_appreciation=110, dividend_consistency=78, payment_frequency=4, recurring_profit=92, sector_stability=86, pe_ratio=28, pvp=7.1),
    },
]


def seed_demo_data(db: Session) -> None:
    for item in ASSETS:
        asset = db.execute(select(Asset).where(Asset.ticker == item["ticker"])).scalar_one_or_none()
        if asset is None:
            asset = Asset(
                ticker=item["ticker"],
                name=item["name"],
                asset_class=item["asset_class"],
                sector=item["sector"],
                segment=item["segment"],
                last_price=Decimal(str(item["last_price"])),
                provider_symbol=item["ticker"],
            )
            ensure_asset_engine_metadata(db, asset, force=True)
            db.add(asset)
            db.flush()
            ensure_asset_engine_metadata(db, asset)
        else:
            ensure_asset_engine_metadata(db, asset)
        if asset.snapshot is None:
            db.add(MarketSnapshot(asset_id=asset.id, **{key: Decimal(str(value)) if isinstance(value, float) else value for key, value in item["snapshot"].items()}))

    user = db.execute(select(User).where(User.email == "demo@carteiraalpha.com")).scalar_one_or_none()
    if user is not None:
        db.commit()
        return

    user = User(
        email="demo@carteiraalpha.com",
        full_name="Investidor Alpha",
        password_hash=hash_password("Carteira@123"),
    )
    db.add(user)
    db.flush()

    assets = {asset.ticker: asset for asset in db.execute(select(Asset)).scalars().all()}
    transactions = [
        ("TAEE11", "buy", 17, 240, 31.9, 7.2, "Alpha Corretora"),
        ("TAEE11", "buy", 8, 120, 34.2, 5.4, "Alpha Corretora"),
        ("ITSA4", "buy", 16, 1200, 8.9, 4.8, "BTG Pactual"),
        ("ITSA4", "buy", 5, 600, 9.8, 4.2, "BTG Pactual"),
        ("PETR4", "buy", 15, 260, 29.4, 6.0, "Rico"),
        ("PETR4", "sell", 3, 60, 40.1, 3.0, "Rico"),
        ("HGLG11", "buy", 14, 55, 151.2, 8.0, "Alpha Corretora"),
        ("HGLG11", "buy", 4, 18, 160.4, 5.0, "Alpha Corretora"),
        ("KNRI11", "buy", 13, 50, 143.7, 7.0, "Clear"),
        ("IVVB11", "buy", 12, 34, 268.5, 6.0, "BTG Pactual"),
        ("BOVA11", "buy", 11, 70, 113.2, 5.0, "BTG Pactual"),
        ("WEGE3", "buy", 10, 180, 36.8, 5.5, "NuInvest"),
    ]
    for ticker, tx_type, ago, qty, price, fees, broker in transactions:
        db.add(
            Transaction(
                user_id=user.id,
                asset_id=assets[ticker].id,
                type=tx_type,
                date=months_ago(ago),
                quantity=Decimal(str(qty)),
                price=Decimal(str(price)),
                fees=Decimal(str(fees)),
                broker=broker,
            )
        )

    dividends = [
        ("TAEE11", 10, 0.62, 223.2),
        ("TAEE11", 6, 0.55, 198.0),
        ("TAEE11", 2, 0.72, 259.2),
        ("ITSA4", 9, 0.08, 96.0),
        ("ITSA4", 5, 0.11, 198.0),
        ("PETR4", 7, 1.28, 332.8),
        ("PETR4", 1, 0.96, 192.0),
        ("HGLG11", 11, 1.10, 60.5),
        ("HGLG11", 8, 1.12, 61.6),
        ("HGLG11", 4, 1.15, 83.95),
        ("HGLG11", 1, 1.18, 86.14),
        ("KNRI11", 8, 1.00, 50.0),
        ("KNRI11", 4, 1.03, 51.5),
        ("KNRI11", 1, 1.05, 52.5),
        ("WEGE3", 3, 0.09, 16.2),
    ]
    for ticker, ago, amount_per_share, total_amount in dividends:
        db.add(
            Dividend(
                user_id=user.id,
                asset_id=assets[ticker].id,
                date=months_ago(ago, day=20),
                amount_per_share=Decimal(str(amount_per_share)),
                total_amount=Decimal(str(total_amount)),
                source="seed",
            )
        )

    targets = [
        ("asset", "TAEE11", 14),
        ("asset", "ITSA4", 13),
        ("asset", "PETR4", 10),
        ("asset", "HGLG11", 15),
        ("asset", "KNRI11", 13),
        ("asset", "IVVB11", 15),
        ("asset", "BOVA11", 10),
        ("asset", "WEGE3", 10),
        ("class", "Acoes", 47),
        ("class", "FIIs", 28),
        ("class", "ETFs", 25),
    ]
    for level, key, pct in targets:
        db.add(
            TargetAllocation(
                user_id=user.id,
                level=level,
                target_key=key,
                percentage=Decimal(str(pct)),
                profile="equilibrado",
            )
        )

    alerts = [
        ("price_ceiling", "opportunity", "HGLG11 abaixo do preco-teto", "HGLG11 ficou abaixo do preco-teto configurado para acompanhamento.", "HGLG11"),
        ("concentration", "warning", "PETR4 perto do limite de concentracao", "A exposicao em petroleo e gas merece acompanhamento dentro da politica definida.", "PETR4"),
        ("dividend_cut", "critical", "Reducao de dividendos detectada", "Um ativo da carteira reduziu proventos frente a media recente. Avalie fundamentos antes de agir.", "TAEE11"),
        ("rebalance", "info", "Carteira fora da faixa ideal", "O proximo aporte pode ajudar a aproximar a alocacao do perfil equilibrado.", None),
    ]
    for alert_type, severity, title, message, ticker in alerts:
        db.add(
            Alert(
                user_id=user.id,
                asset_id=assets[ticker].id if ticker else None,
                type=alert_type,
                severity=severity,
                title=title,
                message=message,
            )
        )

    db.commit()
