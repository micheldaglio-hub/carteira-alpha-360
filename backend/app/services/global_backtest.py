from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite, sin

from sqlalchemy.orm import Session

from app.services.alpha_global_equity_screener import GLOBAL_TARGET_WEIGHTS, run_alpha_global_equity_screener
from app.services.market_data.v2.contracts import (
    DATA_TYPE_DIVIDENDS,
    DATA_TYPE_FX_RATE,
    DATA_TYPE_PRICE_HISTORY,
    MarketDataRequest,
)
from app.services.market_data.v2.engine import MarketDataEngine


DEFAULT_GLOBAL_BACKTEST_START = date(2025, 1, 1)
DEFAULT_INITIAL_VALUE_BRL = 1000.0

DIVIDEND_YIELD_ASSUMPTIONS = {
    "MSFT": 0.75,
    "AAPL": 0.45,
    "GOOGL": 0.0,
    "NVDA": 0.03,
    "V": 0.75,
    "JNJ": 3.1,
    "PG": 2.4,
    "KO": 3.0,
    "ASML": 0.9,
    "NVO": 1.0,
    "NESN.SW": 3.0,
    "TSM": 1.6,
    "BHP": 5.0,
}

BDR_PROXY_SYMBOLS = {
    "MSFT": "MSFT34",
    "AAPL": "AAPL34",
    "GOOGL": "GOGL34",
    "NVDA": "NVDC34",
    "V": "VISA34",
    "JNJ": "JNJB34",
    "PG": "PGCO34",
    "KO": "COCA34",
    "ASML": "ASML34",
    "NVO": "N1VO34",
    "TSM": "TSMC34",
    "BHP": "BHPG34",
}

GLOBAL_ETF_PROXY = [
    {"ticker": "IVVB11", "name": "iShares S&P 500 Brasil", "weight": 60, "feeAnnualPct": 0.24},
    {"ticker": "WRLD11", "name": "Investo FTSE Global", "weight": 25, "feeAnnualPct": 0.38},
    {"ticker": "NASD11", "name": "Trend NASDAQ 100", "weight": 15, "feeAnnualPct": 0.30},
]


@dataclass(frozen=True)
class SeriesSource:
    provider: str
    fallback: bool = False


def run_global_backtest(
    db: Session | None = None,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    initial_value_brl: float = DEFAULT_INITIAL_VALUE_BRL,
    refresh_market: bool = False,
    global_portfolio: list[dict] | None = None,
) -> dict:
    start, end = _normalize_range(start_date or DEFAULT_GLOBAL_BACKTEST_START, end_date or date.today())
    initial_value = max(_float(initial_value_brl), 1.0)
    portfolio = global_portfolio or run_alpha_global_equity_screener()["portfolio"]
    weights = _normalize_weights({item["ticker"]: _float(item.get("targetWeight")) for item in portfolio})
    by_ticker = {item["ticker"]: item for item in portfolio}
    checkpoints = _month_checkpoints(start, end)
    engine = MarketDataEngine(db=db) if db is not None and refresh_market else None

    price_histories: dict[str, list[dict]] = {}
    price_sources: dict[str, str] = {}
    bdr_histories: dict[str, list[dict]] = {}
    bdr_sources: dict[str, str] = {}
    dividend_sources: dict[str, str] = {}
    dividend_yields: dict[str, float] = {}
    warnings: list[str] = []

    for ticker, weight in weights.items():
        asset = by_ticker.get(ticker, {})
        currency = asset.get("currency") or "USD"
        history, source = _load_price_history(engine, ticker, asset, start, end)
        price_histories[ticker] = history
        price_sources[ticker] = source.provider
        if source.fallback:
            warnings.append(f"{ticker} sem historico real suficiente; usado historico estrutural Alpha como fallback.")
        dividend_yield, dividend_source = _load_annual_dividend_yield(engine, ticker, asset, start, end)
        dividend_yields[ticker] = dividend_yield
        dividend_sources[ticker] = dividend_source.provider
        if dividend_source.fallback and dividend_yield:
            warnings.append(f"{ticker} sem dividendos historicos suficientes; usado yield anual estimado de {dividend_yield:.2f}% a.a.")
        if currency not in {"USD", "BRL", "CHF"}:
            warnings.append(f"{ticker} usa moeda {currency}; cambio tratado por fallback ate existir provider historico para essa moeda.")
        bdr_ticker = BDR_PROXY_SYMBOLS.get(ticker)
        if bdr_ticker:
            bdr_history, bdr_source = _load_price_history(
                engine,
                bdr_ticker,
                {"currency": "BRL", "exchange": "B3", "asset_class": "BDRs", "provider_symbol": bdr_ticker},
                start,
                end,
            )
            bdr_histories[ticker] = [] if bdr_source.fallback else bdr_history
            bdr_sources[bdr_ticker] = bdr_source.provider

    fx_series = _load_fx_series(engine, start, end, ["USD", "CHF"])
    stock_rows = _build_stock_direct_rows(checkpoints, initial_value, weights, by_ticker, price_histories, dividend_yields, fx_series)
    bdr_rows = _build_bdr_rows(checkpoints, initial_value, weights, by_ticker, price_histories, bdr_histories, dividend_yields, fx_series)
    etf_rows = _build_etf_rows(engine, checkpoints, initial_value, start, end, stock_rows, warnings)
    rows = _merge_rows(checkpoints, stock_rows, bdr_rows, etf_rows, fx_series)
    vehicles = _vehicle_summaries(rows)
    best = max(vehicles, key=lambda item: item["totalReturnPct"], default={})
    coverage = _coverage(price_sources, dividend_sources, fx_series)

    try:
        if db is not None and refresh_market:
            db.commit()
    except Exception:
        db.rollback()

    return {
        "id": f"global-backtest-{start.isoformat()}-{end.isoformat()}",
        "title": "Backtest internacional com cambio",
        "status": "foundation_ready",
        "mode": "global_stock_bdr_etf_comparison",
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "initialValueBrl": round(initial_value, 2),
        "currency": "BRL",
        "baseCurrency": "BRL",
        "rows": rows,
        "vehicles": vehicles,
        "summary": {
            "bestVehicle": best.get("id", ""),
            "bestVehicleLabel": best.get("label", ""),
            "bestReturnPct": best.get("totalReturnPct", 0),
            "startUsdBrl": rows[0]["usdBrl"] if rows else 0,
            "endUsdBrl": rows[-1]["usdBrl"] if rows else 0,
            "fxReturnPct": _return_pct(rows[-1]["usdBrl"], rows[0]["usdBrl"]) if len(rows) > 1 else 0,
            "sourceCoverage": coverage,
            "warningsCount": len(warnings),
        },
        "comparison": _comparison_table(),
        "assumptions": [
            "Stock direto simula a cesta internacional em moeda original, convertida para BRL por cambio e com dividendos liquidos reinvestidos.",
            "BDR proxy usa o mesmo ativo economico, cambio USD/BRL e um arrasto anual estimado de estrutura/custos; quando houver historico real do BDR, o motor pode usar o provider.",
            "ETF global usa IVVB11, WRLD11 e NASD11 como cesta de referencia; se faltar historico, usa proxy da carteira global com taxa anual estimada.",
            "Dividendos internacionais consideram retencao padrao simulada de 30% para stocks/BDRs quando nao houver dado tributario especifico.",
            "Historico, cambio, dividendos e impostos sao estudos analiticos. Nao prometem rentabilidade futura.",
        ],
        "warnings": warnings[:10],
        "dataSources": {
            "prices": price_sources,
            "bdrs": bdr_sources,
            "dividends": dividend_sources,
            "fx": fx_series["sources"],
        },
        "bdrProxySymbols": [{"stock": stock, "bdr": bdr} for stock, bdr in BDR_PROXY_SYMBOLS.items()],
        "etfProxy": GLOBAL_ETF_PROXY,
    }


def _build_stock_direct_rows(
    checkpoints: list[date],
    initial_value: float,
    weights: dict[str, float],
    by_ticker: dict[str, dict],
    histories: dict[str, list[dict]],
    dividend_yields: dict[str, float],
    fx_series: dict,
) -> list[dict]:
    allocations = {ticker: initial_value * weight / 100 for ticker, weight in weights.items()}
    values = dict(allocations)
    cumulative_dividends = 0.0
    rows: list[dict] = []
    previous = checkpoints[0]
    for index, checkpoint in enumerate(checkpoints):
        if index > 0:
            for ticker, value in list(values.items()):
                asset = by_ticker.get(ticker, {})
                currency = asset.get("currency") or "USD"
                price_ratio = _price_ratio(histories.get(ticker) or [], previous, checkpoint)
                fx_ratio = _fx_at(fx_series, currency, checkpoint) / _fx_at(fx_series, currency, previous)
                values[ticker] = value * price_ratio * fx_ratio
                dividend = values[ticker] * (_float(dividend_yields.get(ticker)) / 100) / 12 * 0.70
                values[ticker] += dividend
                cumulative_dividends += dividend
        total = sum(values.values())
        rows.append(
            {
                "date": checkpoint,
                "value": round(total, 2),
                "returnPct": _return_pct(total, initial_value),
                "dividendsBrl": round(cumulative_dividends, 2),
            }
        )
        previous = checkpoint
    return rows


def _build_bdr_rows(
    checkpoints: list[date],
    initial_value: float,
    weights: dict[str, float],
    by_ticker: dict[str, dict],
    histories: dict[str, list[dict]],
    bdr_histories: dict[str, list[dict]],
    dividend_yields: dict[str, float],
    fx_series: dict,
) -> list[dict]:
    allocations = {ticker: initial_value * weight / 100 for ticker, weight in weights.items()}
    values = dict(allocations)
    cumulative_dividends = 0.0
    annual_drag = 0.35 / 100
    rows: list[dict] = []
    previous = checkpoints[0]
    for index, checkpoint in enumerate(checkpoints):
        if index > 0:
            for ticker, value in list(values.items()):
                real_bdr_history = bdr_histories.get(ticker) or []
                if real_bdr_history:
                    price_ratio = _price_ratio(real_bdr_history, previous, checkpoint)
                    fx_ratio = 1.0
                else:
                    asset = by_ticker.get(ticker, {})
                    currency = asset.get("currency") or "USD"
                    price_ratio = _price_ratio(histories.get(ticker) or [], previous, checkpoint)
                    fx_ratio = _fx_at(fx_series, currency, checkpoint) / _fx_at(fx_series, currency, previous)
                period_drag = _period_drag(previous, checkpoint, annual_drag)
                values[ticker] = value * price_ratio * fx_ratio * period_drag
                dividend = values[ticker] * (_float(dividend_yields.get(ticker)) / 100) / 12 * 0.70 * 0.95
                values[ticker] += dividend
                cumulative_dividends += dividend
        total = sum(values.values())
        rows.append(
            {
                "date": checkpoint,
                "value": round(total, 2),
                "returnPct": _return_pct(total, initial_value),
                "dividendsBrl": round(cumulative_dividends, 2),
            }
        )
        previous = checkpoint
    return rows


def _build_etf_rows(
    engine: MarketDataEngine | None,
    checkpoints: list[date],
    initial_value: float,
    start: date,
    end: date,
    stock_rows: list[dict],
    warnings: list[str],
) -> list[dict]:
    etf_histories: dict[str, list[dict]] = {}
    etf_sources: dict[str, SeriesSource] = {}
    for etf in GLOBAL_ETF_PROXY:
        history, source = _load_price_history(engine, etf["ticker"], {"currency": "BRL", "exchange": "B3", "asset_class": "ETFs"}, start, end)
        etf_histories[etf["ticker"]] = history
        etf_sources[etf["ticker"]] = source
        if source.fallback:
            warnings.append(f"{etf['ticker']} sem historico real suficiente; ETF global usa proxy da carteira internacional com taxa estimada.")

    use_real_etf = any(not source.fallback for source in etf_sources.values())
    annual_fee = sum(etf["feeAnnualPct"] * etf["weight"] / 100 for etf in GLOBAL_ETF_PROXY) / 100
    rows: list[dict] = []
    value = initial_value
    previous = checkpoints[0]
    for index, checkpoint in enumerate(checkpoints):
        if index > 0:
            if use_real_etf:
                weighted_ratio = 0.0
                for etf in GLOBAL_ETF_PROXY:
                    history = etf_histories.get(etf["ticker"]) or []
                    weighted_ratio += _price_ratio(history, previous, checkpoint) * etf["weight"] / 100
                value *= weighted_ratio if weighted_ratio else 1
            else:
                previous_stock = stock_rows[index - 1]["value"]
                current_stock = stock_rows[index]["value"]
                value *= current_stock / previous_stock if previous_stock else 1
            value *= _period_drag(previous, checkpoint, annual_fee)
        rows.append(
            {
                "date": checkpoint,
                "value": round(value, 2),
                "returnPct": _return_pct(value, initial_value),
                "dividendsBrl": 0.0,
            }
        )
        previous = checkpoint
    return rows


def _merge_rows(checkpoints: list[date], stock_rows: list[dict], bdr_rows: list[dict], etf_rows: list[dict], fx_series: dict) -> list[dict]:
    rows = []
    for index, checkpoint in enumerate(checkpoints):
        rows.append(
            {
                "month": f"{checkpoint.year}-{checkpoint.month:02d}",
                "date": checkpoint.isoformat(),
                "stockDirectValue": stock_rows[index]["value"],
                "bdrValue": bdr_rows[index]["value"],
                "globalEtfValue": etf_rows[index]["value"],
                "stockDirectReturnPct": stock_rows[index]["returnPct"],
                "bdrReturnPct": bdr_rows[index]["returnPct"],
                "globalEtfReturnPct": etf_rows[index]["returnPct"],
                "stockDirectDividendsBrl": stock_rows[index]["dividendsBrl"],
                "bdrDividendsBrl": bdr_rows[index]["dividendsBrl"],
                "etfEmbeddedDividendsBrl": etf_rows[index]["dividendsBrl"],
                "usdBrl": round(_fx_at(fx_series, "USD", checkpoint), 4),
                "chfBrl": round(_fx_at(fx_series, "CHF", checkpoint), 4),
            }
        )
    return rows


def _vehicle_summaries(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    first = rows[0]
    last = rows[-1]
    specs = [
        ("stock_direct", "Stock direto", "stockDirectValue", "stockDirectDividendsBrl", "Compra no exterior em USD/CHF, com cambio e dividendos liquidos simulados."),
        ("bdr_proxy", "BDR proxy", "bdrValue", "bdrDividendsBrl", "Exposicao via recibos na B3, em BRL, com proxy de custos e dividendos repassados."),
        ("global_etf", "ETF global", "globalEtfValue", "etfEmbeddedDividendsBrl", "Exposicao simplificada via ETF negociado no Brasil; proventos tendem a ficar embutidos/reinvestidos na cota."),
    ]
    summaries = []
    for vehicle_id, label, value_key, dividend_key, description in specs:
        initial = _float(first.get(value_key))
        final = _float(last.get(value_key))
        summaries.append(
            {
                "id": vehicle_id,
                "label": label,
                "initialValue": round(initial, 2),
                "finalValue": round(final, 2),
                "pnl": round(final - initial, 2),
                "totalReturnPct": _return_pct(final, initial),
                "dividendsBrl": round(_float(last.get(dividend_key)), 2),
                "description": description,
            }
        )
    return summaries


def _comparison_table() -> list[dict]:
    return [
        {
            "criterion": "Execucao",
            "stockDirect": "Corretora internacional ou conta global",
            "bdrProxy": "B3 em reais via BDR",
            "globalEtf": "B3 em reais via ETF",
        },
        {
            "criterion": "Cambio",
            "stockDirect": "Exposto diretamente a USD/CHF",
            "bdrProxy": "Exposto ao cambio por tras do recibo",
            "globalEtf": "Exposto ao cambio dentro da cota",
        },
        {
            "criterion": "Dividendos",
            "stockDirect": "Recebidos no exterior e convertidos",
            "bdrProxy": "Repassados quando aplicavel",
            "globalEtf": "Normalmente embutidos/reinvestidos",
        },
        {
            "criterion": "Simplicidade",
            "stockDirect": "Mais operacional",
            "bdrProxy": "Intermediario",
            "globalEtf": "Mais simples",
        },
        {
            "criterion": "Risco de concentracao",
            "stockDirect": "Depende da cesta escolhida",
            "bdrProxy": "Depende dos BDRs disponiveis",
            "globalEtf": "Mais diversificado por construcao",
        },
    ]


def _load_price_history(engine: MarketDataEngine | None, ticker: str, asset: dict, start: date, end: date) -> tuple[list[dict], SeriesSource]:
    if engine is not None:
        request = MarketDataRequest(
            symbol=ticker,
            provider_symbol=asset.get("provider_symbol") or ticker,
            market=asset.get("exchange") or asset.get("market") or "",
            asset_class=asset.get("asset_class") or asset.get("class") or "Acoes",
            currency=asset.get("currency") or "USD",
            start_date=start,
            end_date=end,
            interval="1day",
        )
        records = engine.collect(DATA_TYPE_PRICE_HISTORY, request, include_mock=False)
        for record in records:
            prices = _extract_prices(record.payload.get("prices") or [])
            if len(prices) >= 2:
                return prices, SeriesSource(record.provider)
    return _fallback_history(ticker, start, end), SeriesSource("alpha_fallback", fallback=True)


def _load_annual_dividend_yield(engine: MarketDataEngine | None, ticker: str, asset: dict, start: date, end: date) -> tuple[float, SeriesSource]:
    if engine is not None:
        request = MarketDataRequest(
            symbol=ticker,
            provider_symbol=asset.get("provider_symbol") or ticker,
            market=asset.get("exchange") or asset.get("market") or "",
            asset_class=asset.get("asset_class") or asset.get("class") or "Acoes",
            currency=asset.get("currency") or "USD",
            start_date=start,
            end_date=end,
        )
        records = engine.collect(DATA_TYPE_DIVIDENDS, request, include_mock=False)
        for record in records:
            dividends = record.payload.get("dividends") or []
            annual = _annualized_dividend_yield(dividends, ticker)
            if annual > 0:
                return annual, SeriesSource(record.provider)
    return _float(DIVIDEND_YIELD_ASSUMPTIONS.get(ticker)), SeriesSource("alpha_assumption", fallback=True)


def _load_fx_series(engine: MarketDataEngine | None, start: date, end: date, currencies: list[str]) -> dict:
    series = {"sources": {}}
    for currency in currencies:
        if currency == "BRL":
            continue
        current_rate = 0.0
        provider = "alpha_fx_fallback"
        if engine is not None:
            request = MarketDataRequest(symbol=currency, base_currency=currency, quote_currency="BRL", currency="BRL")
            records = engine.collect(DATA_TYPE_FX_RATE, request, include_mock=False)
            for record in records:
                rate = _float(record.payload.get("rate"))
                if rate > 0:
                    current_rate = rate
                    provider = record.provider
                    break
        series[currency] = _fallback_fx_curve(currency, start, end, current_rate)
        series["sources"][f"{currency}/BRL"] = provider
    series["BRL"] = [{"date": start, "rate": 1.0}, {"date": end, "rate": 1.0}]
    return series


def _fallback_history(ticker: str, start: date, end: date) -> list[dict]:
    checkpoints = _month_checkpoints(start, end)
    seed = sum(ord(char) for char in ticker)
    annual_bias = ((seed % 17) - 5) / 100
    volatility = 0.018 + (seed % 7) / 1000
    value = 100.0
    rows = [{"date": checkpoints[0], "close": value}]
    for index, checkpoint in enumerate(checkpoints[1:], start=1):
        monthly = annual_bias / 12 + sin(index * 0.9 + seed % 5) * volatility
        value *= max(0.72, 1 + monthly)
        rows.append({"date": checkpoint, "close": round(value, 4)})
    return rows


def _fallback_fx_curve(currency: str, start: date, end: date, current_rate: float = 0) -> list[dict]:
    checkpoints = _month_checkpoints(start, end)
    default_end = {"USD": 5.35, "CHF": 5.95}.get(currency, 1.0)
    end_rate = current_rate if current_rate > 0 else default_end
    start_rate = {"USD": 5.10, "CHF": 5.65}.get(currency, end_rate)
    rows = []
    total_steps = max(len(checkpoints) - 1, 1)
    for index, checkpoint in enumerate(checkpoints):
        progress = index / total_steps
        wave = sin(index * 0.8) * 0.025
        rate = start_rate + (end_rate - start_rate) * progress + wave
        rows.append({"date": checkpoint, "rate": round(max(rate, 0.0001), 4)})
    return rows


def _annualized_dividend_yield(dividends: list[dict], ticker: str) -> float:
    total = sum(_float(row.get("amount")) for row in dividends)
    if total <= 0:
        return 0
    reference_price = 100.0
    return min(12.0, max(0.0, total / reference_price * 100))


def _coverage(price_sources: dict[str, str], dividend_sources: dict[str, str], fx_series: dict) -> dict:
    real_prices = sum(1 for provider in price_sources.values() if "fallback" not in provider)
    real_dividends = sum(1 for provider in dividend_sources.values() if "assumption" not in provider and "fallback" not in provider)
    return {
        "priceReal": real_prices,
        "priceTotal": len(price_sources),
        "dividendReal": real_dividends,
        "dividendTotal": len(dividend_sources),
        "fxSources": fx_series.get("sources") or {},
    }


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(_float(value), 0.0) for value in weights.values())
    if total <= 0:
        return {}
    return {ticker: max(_float(value), 0.0) / total * 100 for ticker, value in weights.items()}


def _period_drag(previous: date, checkpoint: date, annual_drag: float) -> float:
    days = max((checkpoint - previous).days, 0)
    return max(0.0, 1 - annual_drag * days / 365)


def _price_ratio(history: list[dict], previous: date, checkpoint: date) -> float:
    previous_price = _value_at(history, previous, "close")
    current_price = _value_at(history, checkpoint, "close")
    return current_price / previous_price if previous_price else 1.0


def _fx_at(series: dict, currency: str, target: date) -> float:
    if currency == "BRL":
        return 1.0
    return _value_at(series.get(currency) or [], target, "rate") or 1.0


def _value_at(rows: list[dict], target: date, key: str) -> float:
    selected = None
    for row in sorted(rows, key=lambda item: item["date"]):
        if row["date"] <= target:
            selected = row
        else:
            break
    if selected is None and rows:
        selected = sorted(rows, key=lambda item: item["date"])[0]
    return _float(selected.get(key) if selected else 0)


def _extract_prices(rows: list[dict]) -> list[dict]:
    prices = []
    for row in rows:
        try:
            day = date.fromisoformat(str(row.get("date"))[:10])
        except Exception:
            continue
        close = _float(row.get("close"))
        if close <= 0:
            continue
        prices.append({"date": day, "close": close})
    return sorted(prices, key=lambda item: item["date"])


def _month_checkpoints(start: date, end: date) -> list[date]:
    checkpoints = [start]
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        month_end = _last_day_of_month(cursor)
        checkpoint = min(month_end, end)
        if checkpoint > checkpoints[-1]:
            checkpoints.append(checkpoint)
        cursor = _add_month(cursor)
    return checkpoints


def _last_day_of_month(day: date) -> date:
    return _add_month(date(day.year, day.month, 1)) - timedelta(days=1)


def _add_month(day: date) -> date:
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _normalize_range(start_date: date, end_date: date) -> tuple[date, date]:
    today = date.today()
    start = min(start_date, end_date)
    end = max(start_date, end_date)
    if end > today:
        end = today
    if start < date(2000, 1, 1):
        start = date(2000, 1, 1)
    if start == end:
        end = min(today, start + timedelta(days=31))
    return start, end


def _return_pct(value: float, base: float) -> float:
    if not base:
        return 0.0
    return round((value / base - 1) * 100, 2)


def _float(value) -> float:
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0.0
    except Exception:
        return 0.0
