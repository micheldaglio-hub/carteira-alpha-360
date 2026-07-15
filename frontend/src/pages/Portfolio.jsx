import { Bitcoin, BriefcaseBusiness, Layers3, PlusCircle, RefreshCw, Save, TrendingUp, Trash2, WalletCards } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import { apiFetch } from "../lib/api.js";
import { currency, pct } from "../lib/format.js";

const today = new Date().toISOString().slice(0, 10);
const defaultBacktestStart = "2025-01-01";
const axisTick = { fontSize: 11, fill: "var(--muted)", fontWeight: 600 };
const currentMonthLabel = new Date().toLocaleDateString("pt-BR", { month: "long" });
const backtestReturnViews = [
  {
    id: "risk",
    label: "Sem renda fixa",
    shortLabel: "sem renda fixa",
    dataKey: "riskAssetsReturnPct",
    summaryKey: "riskAssetsReturnPct",
    averageKey: "averageRiskAssetsMonthlyReturnPct",
    annualizedKey: "annualizedRiskAssetsReturnPct",
    monthlyEquivalentKey: "monthlyEquivalentRiskAssetsReturnPct",
    hint: "Acoes + cripto, sem o RDB diluir o percentual.",
  },
  {
    id: "total",
    label: "Consolidado",
    shortLabel: "consolidado",
    dataKey: "monthlyReturnPct",
    summaryKey: "totalReturnPct",
    averageKey: "averageMonthlyReturnPct",
    annualizedKey: "annualizedTotalReturnPct",
    monthlyEquivalentKey: "monthlyEquivalentTotalReturnPct",
    hint: "Carteira inteira, incluindo renda fixa.",
  },
  {
    id: "stocks",
    label: "Acoes",
    shortLabel: "acoes",
    dataKey: "stocksReturnPct",
    summaryKey: "stocksReturnPct",
    averageKey: "averageStocksMonthlyReturnPct",
    annualizedKey: "annualizedStocksReturnPct",
    monthlyEquivalentKey: "monthlyEquivalentStocksReturnPct",
    hint: "Somente ativos de bolsa.",
  },
  {
    id: "crypto",
    label: "Cripto",
    shortLabel: "cripto",
    dataKey: "cryptoReturnPct",
    summaryKey: "cryptoReturnPct",
    averageKey: "averageCryptoMonthlyReturnPct",
    annualizedKey: "annualizedCryptoReturnPct",
    monthlyEquivalentKey: "monthlyEquivalentCryptoReturnPct",
    hint: "Somente criptomoedas.",
  },
  {
    id: "fixedIncome",
    label: "Renda fixa",
    shortLabel: "renda fixa",
    dataKey: "fixedIncomeReturnPct",
    summaryKey: "fixedIncomeReturnPct",
    averageKey: "averageFixedIncomeMonthlyReturnPct",
    annualizedKey: "annualizedFixedIncomeReturnPct",
    monthlyEquivalentKey: "monthlyEquivalentFixedIncomeReturnPct",
    hint: "Somente RDB/CDI cadastrado.",
  },
];
const backtestReturnViewMap = Object.fromEntries(backtestReturnViews.map((item) => [item.id, item]));

const initialForm = {
  ticker: "TAEE11",
  asset_name: "Taesa Units",
  asset_class: "Acoes",
  sector: "Energia eletrica",
  segment: "Transmissao",
  type: "buy",
  date: today,
  quantity: "10",
  price: "35.16",
  fees: "0",
  broker: "Alpha Corretora",
  notes: "",
};

function formatQuantity(value) {
  return Number(value || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  });
}

function isCryptoPosition(position) {
  return ["cripto", "crypto"].includes(String(position?.class || "").toLowerCase());
}

function isFixedIncomePosition(position) {
  const assetClass = String(position?.class || "").toLowerCase();
  return assetClass.includes("renda fixa") || ["fixed income", "cdb", "rdb", "tesouro"].includes(assetClass);
}

function isExchangePosition(position) {
  return !isCryptoPosition(position) && !isFixedIncomePosition(position);
}

function aggregatePositions(positions) {
  const totals = positions.reduce(
    (acc, position) => ({
      assetCount: acc.assetCount + 1,
      quantity: acc.quantity + Number(position.quantity || 0),
      investedValue: acc.investedValue + Number(position.investedValue || 0),
      currentValue: acc.currentValue + Number(position.currentValue || 0),
      pnl: acc.pnl + Number(position.pnl || 0),
      monthStartValue: acc.monthStartValue + Number(position.monthStartValue || 0),
      monthPnl: acc.monthPnl + Number(position.monthPnl || 0),
    }),
    { assetCount: 0, quantity: 0, investedValue: 0, currentValue: 0, pnl: 0, monthStartValue: 0, monthPnl: 0 }
  );
  totals.returnPct = totals.investedValue ? (totals.pnl / totals.investedValue) * 100 : 0;
  totals.monthReturnPct = totals.monthStartValue ? (totals.monthPnl / totals.monthStartValue) * 100 : 0;
  return totals;
}

function SummaryCard({ label, value, hint, icon: Icon, tone = "amber" }) {
  const tones = {
    amber: "border-amber-400/40 bg-amber-500/10 text-amber-300",
    emerald: "border-emerald-400/40 bg-emerald-500/10 text-emerald-300",
    rose: "border-rose-400/40 bg-rose-500/10 text-rose-300",
    sky: "border-sky-400/40 bg-sky-500/10 text-sky-300",
    stone: "border-stone-400/40 bg-stone-500/10 text-stone-300",
  };
  return (
    <div className="surface min-h-[5.8rem] p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-stone-500">{label}</p>
        <span className={`flex h-7 w-7 items-center justify-center rounded-lg border ${tones[tone] || tones.amber}`}>
          <Icon size={14} />
        </span>
      </div>
      <p className="mt-1.5 text-lg font-semibold leading-tight text-stone-950">{value}</p>
      <p className="mt-0.5 text-[0.68rem] leading-4 text-stone-500">{hint}</p>
    </div>
  );
}

function BacktestLineTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const rows = payload.filter((item) => item.value !== undefined && item.value !== null);
  const meta = payload[0]?.payload || {};
  return (
    <div className="portfolio-backtest-tooltip">
      <p className="portfolio-backtest-tooltip__label">{label}</p>
      {rows.map((item) => (
        <div key={item.dataKey} className="portfolio-backtest-tooltip__row">
          <span className="portfolio-backtest-tooltip__dot" style={{ backgroundColor: item.color }} />
          <span>{item.name}</span>
          <strong>{currency.format(item.value || 0)}</strong>
        </div>
      ))}
      {(meta.totalContributed || 0) > 0 ? (
        <div className="portfolio-backtest-tooltip__row portfolio-backtest-tooltip__row--muted">
          <span className="portfolio-backtest-tooltip__dot" style={{ backgroundColor: "#f5c84b" }} />
          <span>Aportes acumulados</span>
          <strong>{currency.format(meta.totalContributed || 0)}</strong>
        </div>
      ) : null}
    </div>
  );
}

function BacktestBarTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const value = Number(payload[0]?.value || 0);
  const name = payload[0]?.name || "Retorno mensal";
  return (
    <div className="portfolio-backtest-tooltip">
      <p className="portfolio-backtest-tooltip__label">{label}</p>
      <div className="portfolio-backtest-tooltip__row">
        <span className="portfolio-backtest-tooltip__dot" style={{ backgroundColor: value >= 0 ? "#3bd19f" : "#f97373" }} />
        <span>{name}</span>
        <strong className={value >= 0 ? "text-emerald-300" : "text-rose-300"}>{pct(value)}</strong>
      </div>
    </div>
  );
}

export default function Portfolio({ token }) {
  const [data, setData] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [deletingAssetId, setDeletingAssetId] = useState("");
  const [backtest, setBacktest] = useState(null);
  const [backtestForm, setBacktestForm] = useState({ start_date: defaultBacktestStart, end_date: today });
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestError, setBacktestError] = useState("");
  const [backtestReturnView, setBacktestReturnView] = useState("risk");

  const load = () => {
    setError("");
    return apiFetch("/portfolio", { token }).then(setData).catch((err) => setError(err.message));
  };

  useEffect(() => {
    load();
    runBacktest({ start_date: defaultBacktestStart, end_date: today });
  }, [token]);

  const totals = useMemo(() => data?.totals || {}, [data]);
  const equityPositions = useMemo(() => (data?.positions || []).filter(isExchangePosition), [data]);
  const fixedIncomePositions = useMemo(() => (data?.positions || []).filter(isFixedIncomePosition), [data]);
  const cryptoPositions = useMemo(() => (data?.positions || []).filter(isCryptoPosition), [data]);
  const equitySummary = useMemo(() => aggregatePositions(equityPositions), [equityPositions]);
  const fixedIncomeSummary = useMemo(() => aggregatePositions(fixedIncomePositions), [fixedIncomePositions]);
  const cryptoSummary = useMemo(() => aggregatePositions(cryptoPositions), [cryptoPositions]);
  const backtestRows = backtest?.rows || [];
  const selectedBacktestReturnView = backtestReturnViewMap[backtestReturnView] || backtestReturnViewMap.risk;
  const selectedBacktestReturnPct = Number(backtest?.summary?.[selectedBacktestReturnView.summaryKey] || 0);
  const selectedBacktestAveragePct = Number(backtest?.summary?.[selectedBacktestReturnView.averageKey] || 0);
  const selectedBacktestAnnualizedPct = Number(backtest?.summary?.[selectedBacktestReturnView.annualizedKey] || 0);
  const selectedBacktestMonthlyEquivalentPct = Number(backtest?.summary?.[selectedBacktestReturnView.monthlyEquivalentKey] || 0);
  const totalReturnKeys = {
    risk: "riskAssetsReturnWithIncomePct",
    total: "totalReturnWithIncomePct",
    stocks: "stocksReturnWithIncomePct",
    crypto: "cryptoReturnWithIncomePct",
    fixedIncome: "fixedIncomeReturnWithIncomePct",
  };
  const selectedBacktestReturnWithIncomePct = Number(backtest?.summary?.[totalReturnKeys[selectedBacktestReturnView.id]] || 0);
  const backtestIncomeBreakdown = backtest?.summary?.incomeBreakdown || {};
  const backtestDataConfidence = backtest?.dataConfidence || {};

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setStatus("");
    setError("");
    try {
      await apiFetch("/portfolio/transactions", {
        method: "POST",
        token,
        body: {
          ...form,
          quantity: Number(form.quantity),
          price: Number(form.price),
          fees: Number(form.fees || 0),
        },
      });
      setStatus("Movimentacao registrada com sucesso.");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function removePosition(position) {
    const confirmed = window.confirm(
      `Remover ${position.ticker} da sua carteira? Isso apaga movimentacoes, proventos, alertas e metas desse ativo apenas para o seu usuario.`
    );
    if (!confirmed) return;

    setDeletingAssetId(position.assetId);
    setStatus("");
    setError("");
    try {
      const result = await apiFetch(`/portfolio/positions/${position.assetId}`, { method: "DELETE", token });
      setStatus(result.message || "Posicao removida da carteira.");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingAssetId("");
    }
  }

  async function runBacktest(payload = backtestForm) {
    setBacktestLoading(true);
    setBacktestError("");
    try {
      const params = new URLSearchParams({
        start_date: payload.start_date,
        end_date: payload.end_date || today,
      });
      const result = await apiFetch(`/portfolio/backtest?${params.toString()}`, { token });
      setBacktest(result);
      setBacktestError("");
    } catch (err) {
      setBacktestError(err.message);
    } finally {
      setBacktestLoading(false);
    }
  }

  if (!data && !error) return <LoadingState />;

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Minha Carteira</p>
          <h2 className="text-2xl font-semibold text-stone-950">Minha carteira de investimentos</h2>
        </div>
        <button onClick={load} className="btn-secondary h-10 px-3 text-sm">
          <RefreshCw size={16} />
          Atualizar
        </button>
      </header>

      {error ? <ErrorState message={error} /> : null}

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <SummaryCard
          label="Valor atual acoes"
          value={currency.format(equitySummary.currentValue || 0)}
          hint={`Investido: ${currency.format(equitySummary.investedValue || 0)}`}
          icon={WalletCards}
          tone="amber"
        />
        <SummaryCard
          label="Ativos de bolsa"
          value={`${equitySummary.assetCount || 0} ativos`}
          hint={`Desde compra: ${pct(equitySummary.returnPct)} | Qtd.: ${formatQuantity(equitySummary.quantity)}`}
          icon={BriefcaseBusiness}
          tone="sky"
        />
        <SummaryCard
          label="Renda fixa"
          value={currency.format(fixedIncomeSummary.currentValue || 0)}
          hint={`Rent. atual: ${pct(fixedIncomeSummary.returnPct)} | Ganho: ${currency.format(fixedIncomeSummary.pnl || 0)}`}
          icon={WalletCards}
          tone="emerald"
        />
        <SummaryCard
          label="Cripto"
          value={currency.format(cryptoSummary.currentValue || 0)}
          hint={`${cryptoSummary.assetCount || 0} ativos | Rent. atual: ${pct(cryptoSummary.returnPct)}`}
          icon={Bitcoin}
          tone={(cryptoSummary.pnl || 0) >= 0 ? "emerald" : "amber"}
        />
        <SummaryCard
          label="Rent. acoes no mes"
          value={pct(equitySummary.monthReturnPct)}
          hint={`${currentMonthLabel}: ${currency.format(equitySummary.monthPnl || 0)} | Desde compra: ${pct(equitySummary.returnPct)}`}
          icon={TrendingUp}
          tone={(equitySummary.monthPnl || 0) >= 0 ? "emerald" : "rose"}
        />
      </section>

      <section className="surface p-4">
        <div className="mb-4 flex items-center gap-2">
          <PlusCircle size={18} className="text-amber-700" />
          <h3 className="font-semibold text-stone-950">Registrar compra ou venda de acoes</h3>
        </div>
        <form onSubmit={submit} className="grid gap-3 md:grid-cols-4 xl:grid-cols-12">
          <input
            className="field xl:col-span-2"
            value={form.ticker}
            onChange={(event) => setForm({ ...form, ticker: event.target.value.toUpperCase() })}
            placeholder="Ticker"
          />
          <input
            className="field xl:col-span-2"
            value={form.asset_name}
            onChange={(event) => setForm({ ...form, asset_name: event.target.value })}
            placeholder="Nome do ativo"
          />
          <select
            className="field xl:col-span-2"
            value={form.asset_class}
            onChange={(event) => setForm({ ...form, asset_class: event.target.value })}
          >
            <option value="Acoes">Acoes</option>
            <option value="FIIs">FIIs</option>
            <option value="ETFs">ETFs</option>
            <option value="BDRs">BDRs</option>
            <option value="Renda fixa">Renda fixa</option>
            <option value="Outros">Outros</option>
          </select>
          <input
            className="field xl:col-span-2"
            value={form.sector}
            onChange={(event) => setForm({ ...form, sector: event.target.value })}
            placeholder="Setor"
          />
          <input
            className="field xl:col-span-2"
            value={form.segment}
            onChange={(event) => setForm({ ...form, segment: event.target.value })}
            placeholder="Segmento"
          />
          <select className="field xl:col-span-2" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}>
            <option value="buy">Compra</option>
            <option value="sell">Venda</option>
          </select>
          <input className="field xl:col-span-2" type="date" value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} />
          <input
            className="field xl:col-span-2"
            type="number"
            step="0.0001"
            value={form.quantity}
            onChange={(event) => setForm({ ...form, quantity: event.target.value })}
            placeholder="Quantidade"
          />
          <input
            className="field xl:col-span-2"
            type="number"
            step="0.01"
            value={form.price}
            onChange={(event) => setForm({ ...form, price: event.target.value })}
            placeholder="Preco"
          />
          <input
            className="field xl:col-span-2"
            type="number"
            step="0.01"
            value={form.fees}
            onChange={(event) => setForm({ ...form, fees: event.target.value })}
            placeholder="Taxas"
          />
          <input
            className="field xl:col-span-2"
            value={form.broker}
            onChange={(event) => setForm({ ...form, broker: event.target.value })}
            placeholder="Corretora"
          />
          <button className="btn-primary h-12 px-4 text-sm xl:col-span-2" disabled={loading}>
            <Save size={16} />
            {loading ? "Salvando" : "Salvar"}
          </button>
        </form>
        {status ? <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">{status}</p> : null}
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <h3 className="font-semibold text-stone-950">Ativos de bolsa em carteira</h3>
          <p className="text-xs text-stone-500">Acoes, FIIs, ETFs e BDRs. Renda fixa e cripto ficam em blocos separados.</p>
        </div>
        <div className="overflow-x-auto">
            <table className="w-full min-w-[1280px] text-left text-sm">
              <thead className="bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                {["Ativo", "Classe", "Setor", "Qtd.", "Preco medio", "Preco atual", "Investido", "Atual", "P/L", "Rent. compra", "P/L mes", "Rent. mes", "Proventos PM", "Peso", "Remover"].map((head) => (
                  <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {equityPositions.map((position) => (
                <tr key={position.assetId} className="hover:bg-stone-50">
                  <td className="px-4 py-3">
                    <p className="font-semibold text-stone-950">{position.ticker}</p>
                    <p className="text-xs text-stone-500">{position.name}</p>
                  </td>
                  <td className="px-4 py-3">{position.class}</td>
                  <td className="px-4 py-3">{position.sector}</td>
                  <td className="px-4 py-3">{position.quantity}</td>
                  <td className="px-4 py-3">{currency.format(position.averagePrice)}</td>
                  <td className="px-4 py-3">{currency.format(position.currentPrice)}</td>
                  <td className="px-4 py-3">{currency.format(position.investedValue)}</td>
                  <td className="px-4 py-3">{currency.format(position.currentValue)}</td>
                  <td className={`px-4 py-3 font-semibold ${position.pnl >= 0 ? "text-emerald-700" : "text-rose-700"}`}>{currency.format(position.pnl)}</td>
                  <td className="px-4 py-3">{pct(position.returnPct)}</td>
                  <td className={`px-4 py-3 font-semibold ${(position.monthPnl || 0) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>{currency.format(position.monthPnl || 0)}</td>
                  <td className="px-4 py-3" title={`Fonte: ${position.monthPerformanceSource || "indisponivel"}`}>{pct(position.monthReturnPct || 0)}</td>
                  <td className="px-4 py-3">{pct(position.dividendYieldOnAvg)}</td>
                  <td className="px-4 py-3">{pct(position.weight)}</td>
                  <td className="px-4 py-3">
                    <button
                      className="icon-button"
                      onClick={() => removePosition(position)}
                      disabled={deletingAssetId === position.assetId}
                      title={`Remover ${position.ticker} da carteira`}
                      type="button"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {!equityPositions.length ? (
                <tr>
                  <td className="px-4 py-6 text-sm text-stone-500" colSpan={15}>Nenhum ativo de bolsa cadastrado ainda.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <h3 className="font-semibold text-stone-950">Minha renda fixa</h3>
          <p className="text-xs text-stone-500">
            RDB, CDB, Tesouro e outros pos-fixados. Ativos com CDI usam estimativa diaria pelo Banco Central.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1040px] text-left text-sm">
            <thead className="bg-stone-50 text-xs uppercase text-stone-500">
              <tr>
                {["Ativo", "Indexador", "Qtd.", "Valor aplicado", "Valor atual", "Ganho", "Rent.", "Fonte", "Remover"].map((head) => (
                  <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {fixedIncomePositions.map((position) => (
                <tr key={position.assetId} className="hover:bg-stone-50">
                  <td className="px-4 py-3">
                    <p className="font-semibold text-stone-950">{position.ticker}</p>
                    <p className="text-xs text-stone-500">{position.name}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="font-semibold text-stone-950">
                      {position.fixedIncome?.indexer || "Renda fixa"} {position.fixedIncome?.cdiPercent ? `${position.fixedIncome.cdiPercent}%` : ""}
                    </p>
                    <p className="text-xs text-stone-500">{position.sector}</p>
                  </td>
                  <td className="px-4 py-3">{position.quantity}</td>
                  <td className="px-4 py-3">{currency.format(position.investedValue)}</td>
                  <td className="px-4 py-3">{currency.format(position.currentValue)}</td>
                  <td className={`px-4 py-3 font-semibold ${position.pnl >= 0 ? "text-emerald-700" : "text-rose-700"}`}>{currency.format(position.pnl)}</td>
                  <td className="px-4 py-3">{pct(position.returnPct)}</td>
                  <td className="px-4 py-3">
                    <p className="text-xs text-stone-500">{position.fixedIncome?.source || "Cadastro manual"}</p>
                    {position.fixedIncome?.appliedDays ? <p className="text-xs text-stone-500">{position.fixedIncome.appliedDays} dias CDI</p> : null}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      className="icon-button"
                      onClick={() => removePosition(position)}
                      disabled={deletingAssetId === position.assetId}
                      title={`Remover ${position.ticker} da carteira`}
                      type="button"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {!fixedIncomePositions.length ? (
                <tr>
                  <td className="px-4 py-6 text-sm text-stone-500" colSpan={9}>Nenhuma renda fixa cadastrada ainda.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        <div className="border-t border-stone-200 px-4 py-3 text-xs leading-5 text-stone-500">
          Como funciona: se o setor ou segmento tiver "100% CDI", o sistema calcula uma estimativa diaria acumulando a taxa CDI oficial do Banco Central desde a data da aplicacao.
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <div className="flex items-center gap-2">
            <Bitcoin size={18} className="text-amber-700" />
            <h3 className="font-semibold text-stone-950">Minha carteira de cripto</h3>
          </div>
          <p className="text-xs text-stone-500">Criptomoedas separadas para nao misturar leitura de acoes com ativos de risco mais alto.</p>
        </div>
        <div className="space-y-4 p-4">
          <section className="grid gap-3 md:grid-cols-3">
            <SummaryCard
              label="Valor atual cripto"
              value={currency.format(cryptoSummary.currentValue || 0)}
              hint={`Investido: ${currency.format(cryptoSummary.investedValue || 0)}`}
              icon={Bitcoin}
              tone="amber"
            />
            <SummaryCard
              label="Criptomoedas"
              value={`${cryptoSummary.assetCount || 0} ativos`}
              hint={`Qtd. total: ${formatQuantity(cryptoSummary.quantity)}`}
              icon={WalletCards}
              tone="sky"
            />
            <SummaryCard
              label="P/L cripto"
              value={pct(cryptoSummary.returnPct)}
              hint={`Atual: ${currency.format(cryptoSummary.pnl || 0)}`}
              icon={TrendingUp}
              tone={(cryptoSummary.pnl || 0) >= 0 ? "emerald" : "rose"}
            />
          </section>

          <div className="overflow-x-auto rounded-lg border border-stone-200">
            <table className="w-full min-w-[980px] text-left text-sm">
              <thead className="bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                  {["Cripto", "Qtd.", "Preco medio", "Preco atual", "Investido", "Atual", "P/L", "Rent.", "Peso cripto", "Peso total", "Remover"].map((head) => (
                    <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {cryptoPositions.map((position) => {
                  const cryptoWeight = cryptoSummary.currentValue ? (Number(position.currentValue || 0) / cryptoSummary.currentValue) * 100 : 0;
                  return (
                    <tr key={position.assetId} className="hover:bg-stone-50">
                      <td className="px-4 py-3">
                        <p className="font-semibold text-stone-950">{position.ticker}</p>
                        <p className="text-xs text-stone-500">{position.name}</p>
                      </td>
                      <td className="px-4 py-3">{position.quantity}</td>
                      <td className="px-4 py-3">{currency.format(position.averagePrice)}</td>
                      <td className="px-4 py-3">{currency.format(position.currentPrice)}</td>
                      <td className="px-4 py-3">{currency.format(position.investedValue)}</td>
                      <td className="px-4 py-3">{currency.format(position.currentValue)}</td>
                      <td className={`px-4 py-3 font-semibold ${position.pnl >= 0 ? "text-emerald-700" : "text-rose-700"}`}>{currency.format(position.pnl)}</td>
                      <td className="px-4 py-3">{pct(position.returnPct)}</td>
                      <td className="px-4 py-3">{pct(cryptoWeight)}</td>
                      <td className="px-4 py-3">{pct(position.weight)}</td>
                      <td className="px-4 py-3">
                        <button
                          className="icon-button"
                          onClick={() => removePosition(position)}
                          disabled={deletingAssetId === position.assetId}
                          title={`Remover ${position.ticker} da carteira`}
                          type="button"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {!cryptoPositions.length ? (
                  <tr>
                    <td className="px-4 py-6 text-sm text-stone-500" colSpan={11}>Nenhuma criptomoeda cadastrada ainda.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <h3 className="font-semibold text-stone-950">Backtest da carteira atual</h3>
              <p className="text-xs text-stone-500">
                Simula o valor atual real dos seus ativos desde o periodo escolhido, separando ativos de bolsa, renda fixa, cripto e consolidado.
              </p>
            </div>
            <div className="grid gap-2 sm:grid-cols-[9rem_9rem_auto]">
              <input
                className="field h-10"
                type="date"
                value={backtestForm.start_date}
                onChange={(event) => setBacktestForm({ ...backtestForm, start_date: event.target.value })}
              />
              <input
                className="field h-10"
                type="date"
                value={backtestForm.end_date}
                onChange={(event) => setBacktestForm({ ...backtestForm, end_date: event.target.value })}
              />
              <button className="btn-primary h-10 px-4 text-sm" onClick={() => runBacktest()} disabled={backtestLoading}>
                <TrendingUp size={16} />
                {backtestLoading ? "Calculando" : "Calcular"}
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-4">
          {backtestError ? <ErrorState message={backtestError} /> : null}
          <section className="grid gap-3 md:grid-cols-4">
            <SummaryCard
              label="Valor inicial simulado"
              value={currency.format(backtest?.summary?.initialValue || 0)}
              hint={backtest?.startDate || backtestForm.start_date}
              icon={WalletCards}
              tone="sky"
            />
            <SummaryCard
              label="Valor final simulado"
              value={currency.format(backtest?.summary?.finalValue || 0)}
              hint={(backtest?.summary?.totalContributed || 0) > 0 ? `Inclui ${currency.format(backtest.summary.totalContributed)} em aportes` : (backtest?.endDate || backtestForm.end_date)}
              icon={Layers3}
              tone="amber"
            />
            <SummaryCard
              label={`Retorno ${selectedBacktestReturnView.shortLabel}`}
              value={pct(selectedBacktestReturnPct)}
              hint={`Equiv. composto: ${pct(selectedBacktestAnnualizedPct)} a.a. / ${pct(selectedBacktestMonthlyEquivalentPct)} a.m. Media aritmetica: ${pct(selectedBacktestAveragePct)}.`}
              icon={TrendingUp}
              tone={selectedBacktestReturnPct >= 0 ? "emerald" : "rose"}
            />
            <SummaryCard
              label="Cobertura de dados"
              value={`${backtest?.summary?.realDataAssets || 0}/${backtest?.summary?.assetCount || 0}`}
              hint={`${backtest?.summary?.fallbackAssets || 0} ativos com fallback`}
              icon={RefreshCw}
              tone={(backtest?.summary?.fallbackAssets || 0) ? "amber" : "emerald"}
            />
          </section>

          <div className="portfolio-backtest-note">
            <strong>Como ler:</strong> a simulacao comeca com o valor atual real de cada ativo e adiciona {currency.format(backtest?.summary?.monthlyContribution || 0)} por mes, conforme as premissas salvas na Visao Geral. Retorno acumulado nao deve ser dividido pelos meses para comparar com CDI/poupanca; use o equivalente composto a.a. ou a.m. O consolidado inclui renda fixa; se o RDB for grande, ele dilui a variacao de acoes e cripto.
          </div>

          <section className="grid gap-3 xl:grid-cols-2">
            <div className="rounded-lg border border-amber-400/25 bg-amber-500/10 p-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Total Return auditado</p>
                  <p className="mt-1 text-sm leading-5 text-stone-500">
                    Retorno de preco mais dividendos, JCP e rendimentos cadastrados no sistema.
                  </p>
                </div>
                <div className={`portfolio-return-badge is-inline ${selectedBacktestReturnWithIncomePct >= 0 ? "is-positive" : "is-negative"}`}>
                  <span>com renda</span>
                  <strong>{pct(selectedBacktestReturnWithIncomePct)}</strong>
                </div>
              </div>
              <div className="mt-3 grid gap-2 text-xs sm:grid-cols-4">
                <p className="rounded-md border border-white/10 bg-black/10 px-2 py-2 text-stone-500">
                  Proventos/JCP <strong className="block text-stone-950">{currency.format(backtest?.summary?.incomeTotal || 0)}</strong>
                </p>
                <p className="rounded-md border border-white/10 bg-black/10 px-2 py-2 text-stone-500">
                  Dividendos <strong className="block text-stone-950">{currency.format(backtestIncomeBreakdown.dividend || 0)}</strong>
                </p>
                <p className="rounded-md border border-white/10 bg-black/10 px-2 py-2 text-stone-500">
                  JCP <strong className="block text-stone-950">{currency.format(backtestIncomeBreakdown.jcp || 0)}</strong>
                </p>
                <p className="rounded-md border border-white/10 bg-black/10 px-2 py-2 text-stone-500">
                  FIIs <strong className="block text-stone-950">{currency.format(backtestIncomeBreakdown.fii_income || 0)}</strong>
                </p>
              </div>
            </div>

            <div className="rounded-lg border border-sky-400/25 bg-sky-500/10 p-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-300">Confianca dos dados</p>
                  <p className="mt-1 text-sm leading-5 text-stone-500">
                    Mede se preco, historico, fundamentos, proventos e transacoes tem fonte rastreavel.
                  </p>
                </div>
                <div className="rounded-lg border border-sky-400/30 bg-sky-500/10 px-3 py-2 text-right">
                  <span className="block text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-sky-300">score</span>
                  <strong className="text-lg text-stone-950">{Number(backtestDataConfidence.overallScore || 0).toFixed(0)}/100</strong>
                </div>
              </div>
              <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
                <p className="rounded-md border border-white/10 bg-black/10 px-2 py-2 text-stone-500">
                  Classificacao <strong className="block text-stone-950">{backtestDataConfidence.classification || "Sem auditoria"}</strong>
                </p>
                <p className="rounded-md border border-white/10 bg-black/10 px-2 py-2 text-stone-500">
                  Ativos auditados <strong className="block text-stone-950">{backtestDataConfidence.assetCount || 0}</strong>
                </p>
                <p className="rounded-md border border-white/10 bg-black/10 px-2 py-2 text-stone-500">
                  Com fallback <strong className="block text-stone-950">{backtestDataConfidence.fallbackAssetCount || 0}</strong>
                </p>
              </div>
            </div>
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="portfolio-backtest-chart p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div>
                  <h4 className="font-semibold text-stone-950">Patrimonio retroativo</h4>
                  <p className="text-xs text-stone-500">Ativos de bolsa, renda fixa, cripto e total mes a mes.</p>
                </div>
              </div>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={backtestRows} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                    <XAxis dataKey="periodLabel" tick={axisTick} />
                    <YAxis tickFormatter={(value) => currency.format(value)} tick={axisTick} width={76} />
                    <Tooltip content={<BacktestLineTooltip />} cursor={{ stroke: "rgba(245, 200, 75, 0.55)", strokeWidth: 1 }} />
                    <Legend />
                    <Line type="monotone" dataKey="totalValue" name="Total" stroke="var(--primary)" strokeWidth={2.4} dot={false} />
                    <Line type="monotone" dataKey="stocksValue" name="Acoes" stroke="#74c7ff" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="fixedIncomeValue" name="Renda fixa" stroke="#c4b5fd" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="cryptoValue" name="Cripto" stroke="#3bd19f" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="portfolio-backtest-chart p-3">
              <div className="relative min-h-[5.25rem] pr-28">
                <h4 className="font-semibold text-stone-950">Retorno mes a mes</h4>
                <p className="text-xs text-stone-500">Percentual mensal de {selectedBacktestReturnView.shortLabel}.</p>
                <div className="mt-2 flex flex-wrap gap-1.5 pr-2">
                  {backtestReturnViews.map((view) => (
                    <button
                      key={view.id}
                      type="button"
                      className={`rounded-md border px-2.5 py-1 text-[0.68rem] font-semibold transition ${
                        selectedBacktestReturnView.id === view.id
                          ? "border-amber-300 bg-amber-400 text-stone-950"
                          : "border-white/10 bg-white/5 text-stone-400 hover:border-amber-300/50 hover:text-stone-100"
                      }`}
                      onClick={() => setBacktestReturnView(view.id)}
                    >
                      {view.label}
                    </button>
                  ))}
                </div>
                <div className={`portfolio-return-badge ${selectedBacktestReturnPct >= 0 ? "is-positive" : "is-negative"}`}>
                  <span>{selectedBacktestReturnPct >= 0 ? "Lucro" : "Prejuizo"}</span>
                  <strong>{pct(selectedBacktestReturnPct)}</strong>
                </div>
              </div>
              <div className="mt-2 h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={backtestRows} margin={{ left: 0, right: 12, top: 24, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                    <XAxis dataKey="periodLabel" tick={axisTick} />
                    <YAxis tickFormatter={(value) => `${value}%`} tick={axisTick} width={54} />
                    <Tooltip content={<BacktestBarTooltip />} cursor={{ fill: "rgba(245, 200, 75, 0.10)" }} />
                    <Bar dataKey={selectedBacktestReturnView.dataKey} name={`Retorno ${selectedBacktestReturnView.shortLabel}`} radius={[6, 6, 0, 0]}>
                      {backtestRows.map((row) => (
                        <Cell
                          key={`${selectedBacktestReturnView.id}-${row.month}`}
                          fill={Number(row[selectedBacktestReturnView.dataKey] || 0) >= 0 ? "#3bd19f" : "#f97373"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          {backtest?.warnings?.length ? (
            <div className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-200">
              {backtest.warnings.slice(0, 2).map((warning) => <p key={warning}>{warning}</p>)}
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
