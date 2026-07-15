from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Asset, Dividend, Transaction
from app.services.income import normalize_income_type
from app.wealth_os.contracts import TaxEstimateItem, TaxReport, TaxRule


BRAZIL_STOCK_SALE_EXEMPTION_LIMIT = Decimal("20000")
BRAZIL_STOCK_SWING_TAX_RATE = Decimal("0.15")
BRAZIL_FII_CAPITAL_GAIN_TAX_RATE = Decimal("0.20")
BRAZIL_JCP_WITHHOLDING_RATE = Decimal("0.15")


def build_tax_report(db: Session, user_id: str, *, year: int | None = None, month: int | None = None) -> TaxReport:
    today = date.today()
    selected_year = year or today.year
    selected_month = month
    period = f"{selected_year}-{selected_month:02d}" if selected_month else str(selected_year)

    period_start = date(selected_year, selected_month or 1, 1)
    period_end = _month_end(selected_year, selected_month) if selected_month is not None else date(selected_year, 12, 31)
    dividends = _load_dividends(db, user_id, selected_year, selected_month)
    transactions = _load_transactions(db, user_id, period_end)
    income_items, income_alerts = _estimate_income_tax(dividends)
    gain_items, gain_alerts, gain_gaps = _estimate_capital_gain_tax(transactions, period_start=period_start, period_end=period_end)
    items = [*income_items, *gain_items]

    gross_income = sum(item.grossAmount for item in income_items)
    realized_gain = sum(item.grossAmount for item in gain_items)
    withheld = sum(item.estimatedTax for item in income_items if item.category == "jcp")
    due = sum(item.estimatedTax for item in gain_items)
    net = gross_income + realized_gain - withheld - due
    alerts = [*income_alerts, *gain_alerts]
    data_gaps = [
        *gain_gaps,
        "Day trade, aluguel de acoes, compensacao de prejuizos, DARF ja pago e imposto internacional ainda dependem de campos especificos.",
        "A Tax Engine gera estimativa operacional e nao substitui contador ou declaracao oficial.",
    ]
    status = "estimativa_operacional" if items else "sem_movimento_no_periodo"

    return TaxReport(
        status=status,
        headline=_headline(status, due, withheld, alerts),
        period=period,
        jurisdiction="BR",
        grossIncome=round(gross_income, 2),
        realizedGain=round(realized_gain, 2),
        estimatedWithheldTax=round(withheld, 2),
        estimatedTaxDue=round(due, 2),
        netIncomeAfterEstimatedTax=round(net, 2),
        items=items,
        rules=_tax_rules(),
        alerts=alerts,
        dataGaps=data_gaps,
        updatedAt=datetime.now(timezone.utc).isoformat(),
    )


def _load_dividends(db: Session, user_id: str, year: int, month: int | None) -> list[Dividend]:
    query = select(Dividend).options(joinedload(Dividend.asset)).where(Dividend.user_id == user_id, Dividend.date >= date(year, 1, 1), Dividend.date <= date(year, 12, 31))
    if month is not None:
        query = query.where(Dividend.date >= date(year, month, 1), Dividend.date <= _month_end(year, month))
    return list(db.execute(query).scalars().all())


def _load_transactions(db: Session, user_id: str, period_end: date) -> list[Transaction]:
    query = (
        select(Transaction)
        .options(joinedload(Transaction.asset))
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.date.asc(), Transaction.created_at.asc())
    )
    transactions = list(db.execute(query).scalars().all())
    return [tx for tx in transactions if tx.date <= period_end]


def _estimate_income_tax(dividends: list[Dividend]) -> tuple[list[TaxEstimateItem], list[str]]:
    grouped: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    monthly_dividends: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    alerts: list[str] = []

    for dividend in dividends:
        asset_class = dividend.asset.asset_class if dividend.asset else ""
        classification = normalize_income_type(dividend.source, asset_class)
        amount = Decimal(dividend.total_amount or 0)
        grouped[classification.key] += amount
        if classification.key == "dividend":
            monthly_dividends[f"{dividend.date.year}-{dividend.date.month:02d}"] += amount

    items: list[TaxEstimateItem] = []
    dividend_amount = grouped["dividend"]
    if dividend_amount:
        status = "potencialmente_isento_ou_irrf_por_faixa"
        reading = "Dividendos de acoes brasileiras sao tratados separados de JCP. A partir de 2026, valores elevados exigem verificacao das novas regras de IRRF."
        items.append(_tax_item("income_dividend", "dividendos", "Acoes", dividend_amount, Decimal("0"), Decimal("0"), status, reading, ["Dividend.total_amount", "Dividend.source"]))

    for period, amount in monthly_dividends.items():
        if amount > Decimal("50000"):
            alerts.append(f"Dividendos em {period} passaram de R$ 50 mil; revisar regra vigente de IRRF sobre dividendos elevados.")

    jcp_amount = grouped["jcp"]
    if jcp_amount:
        tax = jcp_amount * BRAZIL_JCP_WITHHOLDING_RATE
        items.append(
            _tax_item(
                "income_jcp",
                "jcp",
                "Acoes",
                jcp_amount,
                jcp_amount,
                tax,
                "irrf_estimado",
                "JCP foi separado de dividendo comum e recebeu estimativa de IRRF de 15%.",
                ["Dividend.total_amount", "Dividend.source=jcp"],
                rate=BRAZIL_JCP_WITHHOLDING_RATE,
            )
        )

    fii_amount = grouped["fii_income"]
    if fii_amount:
        items.append(
            _tax_item(
                "income_fii",
                "rendimentos_fii",
                "FIIs",
                fii_amount,
                Decimal("0"),
                Decimal("0"),
                "isencao_condicional",
                "Rendimentos de FIIs podem ser isentos para pessoa fisica quando os requisitos legais forem atendidos.",
                ["Dividend.total_amount", "Asset.asset_class"],
            )
        )
        alerts.append("Rendimentos de FIIs foram tratados como isencao condicional; ganho de capital na venda de cotas e outra regra.")

    other = grouped["other_income"]
    if other:
        items.append(_tax_item("income_other", "outros_proventos", "Outros", other, other, Decimal("0"), "requer_classificacao", "Provento sem classificacao tributaria automatica.", ["Dividend.source"]))
        alerts.append("Existem proventos sem classificacao tributaria especifica.")

    return items, alerts


def _estimate_capital_gain_tax(transactions: list[Transaction], *, period_start: date, period_end: date) -> tuple[list[TaxEstimateItem], list[str], list[str]]:
    states: dict[str, dict] = {}
    monthly: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(lambda: {"sales": Decimal("0"), "gain": Decimal("0")})
    alerts: list[str] = []
    gaps: list[str] = []

    for tx in sorted(transactions, key=lambda item: (item.date, item.created_at)):
        asset = tx.asset
        if asset is None:
            continue
        state = states.setdefault(asset.id, {"quantity": Decimal("0"), "cost": Decimal("0"), "asset": asset})
        qty = Decimal(tx.quantity or 0)
        gross = qty * Decimal(tx.price or 0)
        fees = Decimal(tx.fees or 0)
        if tx.type == "buy":
            state["quantity"] += qty
            state["cost"] += gross + fees
            continue
        if tx.type != "sell" or state["quantity"] <= 0:
            continue
        sell_qty = min(qty, state["quantity"])
        avg_cost = state["cost"] / state["quantity"] if state["quantity"] else Decimal("0")
        sale_value = sell_qty * Decimal(tx.price or 0) - fees
        cost_basis = avg_cost * sell_qty
        realized_gain = sale_value - cost_basis
        state["quantity"] -= sell_qty
        state["cost"] -= avg_cost * sell_qty

        if period_start <= tx.date <= period_end:
            bucket = _tax_bucket(asset)
            key = (f"{tx.date.year}-{tx.date.month:02d}", bucket)
            monthly[key]["sales"] += sale_value
            monthly[key]["gain"] += realized_gain

    items: list[TaxEstimateItem] = []
    for (period, bucket), values in sorted(monthly.items()):
        sales = values["sales"]
        gain = values["gain"]
        positive_gain = max(gain, Decimal("0"))
        if bucket == "stocks":
            if sales <= BRAZIL_STOCK_SALE_EXEMPTION_LIMIT:
                tax = Decimal("0")
                status = "isento_por_vendas_ate_20k"
                reading = f"Vendas de acoes em {period} ficaram em R$ {sales:.2f}; ganho positivo fica dentro da regra de isencao mensal de R$ 20 mil."
            else:
                tax = positive_gain * BRAZIL_STOCK_SWING_TAX_RATE
                status = "darf_estimado"
                reading = f"Vendas de acoes em {period} passaram de R$ 20 mil; ganho positivo recebeu estimativa de 15%."
            items.append(_tax_item(f"gain_stocks_{period}", "ganho_capital", "Acoes", gain, positive_gain, tax, status, reading, ["Transaction buy/sell", "preco medio"], rate=BRAZIL_STOCK_SWING_TAX_RATE if tax else Decimal("0")))
        elif bucket == "fiis":
            tax = positive_gain * BRAZIL_FII_CAPITAL_GAIN_TAX_RATE
            items.append(_tax_item(f"gain_fiis_{period}", "ganho_capital_fii", "FIIs", gain, positive_gain, tax, "darf_estimado", f"Ganho positivo em FIIs em {period} recebeu estimativa de 20%.", ["Transaction buy/sell", "preco medio"], rate=BRAZIL_FII_CAPITAL_GAIN_TAX_RATE if tax else Decimal("0")))
        else:
            gaps.append(f"Operacoes de {bucket} em {period} ainda exigem regra tributaria especifica.")
            items.append(_tax_item(f"gain_{bucket}_{period}", "ganho_capital_revisao", bucket, gain, positive_gain, Decimal("0"), "requer_regra", "Classe de ativo ainda nao possui regra automatica de imposto neste motor.", ["Transaction buy/sell"]))

    if any(item.estimatedTax > 0 for item in items):
        alerts.append("Existe imposto estimado a pagar por ganho de capital. Confirmar prejuizos compensaveis e DARFs anteriores antes de pagar.")
    return items, alerts, gaps


def _tax_bucket(asset: Asset) -> str:
    asset_class = (asset.asset_class or "").lower()
    if "fii" in asset_class or "reit" in asset_class:
        return "fiis"
    if asset_class in {"acoes", "açoes", "ações", "stocks", "equity"} or "acao" in asset_class or "ação" in asset_class:
        return "stocks"
    if "cripto" in asset_class or "crypto" in asset_class:
        return "crypto"
    if "etf" in asset_class:
        return "etfs"
    return asset.asset_class or "outros"


def _tax_item(
    item_id: str,
    category: str,
    asset_class: str,
    gross: Decimal,
    taxable: Decimal,
    tax: Decimal,
    status: str,
    reading: str,
    data_used: list[str],
    *,
    rate: Decimal = Decimal("0"),
) -> TaxEstimateItem:
    gross_float = float(gross)
    tax_float = float(tax)
    return TaxEstimateItem(
        id=item_id,
        category=category,
        assetClass=asset_class,
        jurisdiction="BR",
        grossAmount=round(gross_float, 2),
        taxableAmount=round(float(taxable), 2),
        estimatedTax=round(tax_float, 2),
        netAmount=round(gross_float - tax_float, 2),
        rate=round(float(rate) * 100, 2),
        status=status,
        reading=reading,
        dataUsed=data_used,
    )


def _tax_rules() -> list[TaxRule]:
    return [
        TaxRule(
            id="br_stock_20k_exemption",
            jurisdiction="BR",
            title="Acoes: limite mensal de vendas",
            summary="Ganhos liquidos em acoes podem ser isentos quando o total de vendas mensais fica ate R$ 20 mil, conforme regra da Receita Federal.",
            rate=15,
            source="Receita Federal - Renda variavel / Isencoes",
            status="implementado_estimativo",
        ),
        TaxRule(
            id="br_jcp_irrf",
            jurisdiction="BR",
            title="JCP: IRRF",
            summary="Juros sobre capital proprio sao tratados separados de dividendos e normalmente sofrem IR retido na fonte.",
            rate=15,
            source="Receita Federal - tabela IRRF / JCP",
            status="implementado_estimativo",
        ),
        TaxRule(
            id="br_fii_capital_gain",
            jurisdiction="BR",
            title="FIIs: ganho de capital",
            summary="Ganho liquido na venda de cotas de FII tem tributacao propria; rendimentos mensais podem ter isencao condicional.",
            rate=20,
            source="Receita Federal - Fundos de investimento no Brasil",
            status="implementado_estimativo",
        ),
        TaxRule(
            id="global_withholding",
            jurisdiction="Global",
            title="Dividendos internacionais",
            summary="Dividendos, withholding tax, acordo fiscal, IOF e cambio ainda entram como lacuna controlada para proximas fases.",
            rate=None,
            source="Tax Engine roadmap",
            status="planejado",
        ),
    ]


def _headline(status: str, due: float, withheld: float, alerts: list[str]) -> str:
    if status == "sem_movimento_no_periodo":
        return "Nenhum evento tributario estimado para o periodo escolhido."
    if due > 0:
        return "Ha imposto estimado a revisar antes do fechamento mensal."
    if withheld > 0:
        return "Ha IRRF estimado em proventos, principalmente JCP."
    if alerts:
        return "Ha pontos tributarios para revisar, mas sem imposto a pagar estimado pelo motor."
    return "Eventos tributarios estimados sem imposto adicional no periodo."


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)
