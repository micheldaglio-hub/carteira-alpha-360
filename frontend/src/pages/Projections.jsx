import { Calculator, Goal, RotateCcw, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import StatCard from "../components/StatCard.jsx";
import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import { apiFetch } from "../lib/api.js";
import { compactCurrency, currency } from "../lib/format.js";

const defaults = {
  initial_wealth: 1000,
  monthly_contribution: 100,
  expected_monthly_return: 1,
  expected_annual_dividend_yield: 7.5,
  reinvest_dividends: true,
  dividend_reinvestment_rate: 100,
  annual_contribution_growth: 0,
  variable_monthly_returns: [],
  variable_annual_dividend_yields: [],
  variable_annual_inflation: [],
  years: 25,
  annual_inflation: 4,
  passive_income_goal: 5000,
};

const STORAGE_KEY = "carteira-alpha-projection-premises-v1";
const axisTick = { fontSize: 11, fill: "var(--muted)" };
const tooltipStyle = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)" };
const tooltipLabelStyle = { color: "var(--primary)" };
const normalizePremises = (premises) => ({
  ...defaults,
  ...(premises || {}),
  variable_monthly_returns: Array.isArray(premises?.variable_monthly_returns) ? premises.variable_monthly_returns : [],
  variable_annual_dividend_yields: Array.isArray(premises?.variable_annual_dividend_yields) ? premises.variable_annual_dividend_yields : [],
  variable_annual_inflation: Array.isArray(premises?.variable_annual_inflation) ? premises.variable_annual_inflation : [],
});
const seriesToText = (values) => (Array.isArray(values) && values.length ? values.join("; ") : "");
const parseSeries = (value) =>
  value
    .split(";")
    .map((item) => Number(item.trim().replace(",", ".")))
    .filter((item) => Number.isFinite(item));
const readLocalPremises = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? normalizePremises(JSON.parse(raw)) : defaults;
  } catch {
    return defaults;
  }
};
const writeLocalPremises = (payload) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Browser storage can be unavailable in restricted contexts.
  }
};
const clearLocalPremises = () => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Keep reset functional even without browser storage.
  }
};

export default function Projections({ token }) {
  const [form, setForm] = useState(() => readLocalPremises());
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");
  const [seriesText, setSeriesText] = useState({
    variable_monthly_returns: seriesToText(readLocalPremises().variable_monthly_returns),
    variable_annual_dividend_yields: seriesToText(readLocalPremises().variable_annual_dividend_yields),
    variable_annual_inflation: seriesToText(readLocalPremises().variable_annual_inflation),
  });

  async function simulate(payload = form) {
    setLoading(true);
    setError("");
    try {
      const result = await apiFetch("/projections/simulate", { method: "POST", token, body: payload });
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    const localPremises = readLocalPremises();

    async function loadPremises() {
      let selected = localPremises;
      try {
        const result = await apiFetch("/projections/premises", { token });
        if (result.premises) {
          selected = normalizePremises(result.premises);
          writeLocalPremises(selected);
          if (active) setSaveStatus("Premissas salvas carregadas");
        }
      } catch {
        if (active && localPremises !== defaults) setSaveStatus("Premissas locais carregadas");
      }

      if (!active) return;
      setForm(selected);
      setSeriesText({
        variable_monthly_returns: seriesToText(selected.variable_monthly_returns),
        variable_annual_dividend_yields: seriesToText(selected.variable_annual_dividend_yields),
        variable_annual_inflation: seriesToText(selected.variable_annual_inflation),
      });
      simulate(selected);
    }

    loadPremises();
    return () => {
      active = false;
    };
  }, [token]);

  const update = (key, value) => {
    setSaveStatus("");
    setForm((current) => {
      if (key === "dividend_reinvestment_rate") {
        return { ...current, [key]: value, reinvest_dividends: value > 0 };
      }
      return { ...current, [key]: value };
    });
  };
  const updateSeries = (key, value) => {
    setSaveStatus("");
    setSeriesText((current) => ({ ...current, [key]: value }));
    update(key, parseSeries(value));
  };
  const saveCurrentPremises = async () => {
    setSaving(true);
    setError("");
    try {
      const result = await apiFetch("/projections/premises", { method: "PUT", token, body: form });
      const saved = normalizePremises(result.premises || form);
      setForm(saved);
      writeLocalPremises(saved);
      setSaveStatus("Premissas salvas");
      await simulate(saved);
    } catch (err) {
      writeLocalPremises(form);
      setSaveStatus("Salvo neste navegador");
      await simulate(form);
    } finally {
      setSaving(false);
    }
  };
  const resetPremises = async () => {
    clearLocalPremises();
    setForm(defaults);
    setSeriesText({
      variable_monthly_returns: "",
      variable_annual_dividend_yields: "",
      variable_annual_inflation: "",
    });
    setSaveStatus("Premissas padrao restauradas");
    try {
      await apiFetch("/projections/premises", { method: "DELETE", token });
    } catch {
      // Local reset is enough for the current session if the backend is unavailable.
    }
    simulate(defaults);
  };

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Projecao financeira</p>
          <h2 className="text-2xl font-semibold text-stone-950">Simulador patrimonial</h2>
        </div>
        <p className="max-w-2xl text-sm leading-6 text-stone-500">
          Ajuste patrimonio inicial, aportes, retorno mensal, proventos, inflacao e meta de renda passiva.
        </p>
      </header>

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <form
          className="surface grid gap-3 p-4 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            simulate();
          }}
        >
          {[
            ["initial_wealth", "Patrimonio inicial", 1000],
            ["monthly_contribution", "Aporte mensal", 100],
            ["expected_monthly_return", "Rentabilidade mensal sem proventos (%)", 0.1],
            ["expected_annual_dividend_yield", "Yield anual de proventos (%)", 0.1],
            ["dividend_reinvestment_rate", "Reinvestimento dos proventos (%)", 1],
            ["annual_contribution_growth", "Aumento anual dos aportes (%)", 0.1],
            ["years", "Prazo em anos", 1],
            ["annual_inflation", "Inflacao anual (%)", 0.1],
            ["passive_income_goal", "Meta renda mensal", 100],
          ].map(([key, label, step]) => (
            <label key={key} className="block">
              <span className="text-xs font-medium text-stone-700">{label}</span>
              <input
                className="field mt-1"
                type="number"
                step={step}
                value={form[key]}
                onChange={(event) => update(key, Number(event.target.value))}
              />
            </label>
          ))}

          <label className="flex min-h-10 items-center gap-2 rounded-lg border border-stone-200 bg-white px-3">
            <input
              type="checkbox"
              checked={form.reinvest_dividends}
              onChange={(event) => {
                setSaveStatus("");
                setForm((current) => ({
                  ...current,
                  reinvest_dividends: event.target.checked,
                  dividend_reinvestment_rate: event.target.checked ? 100 : 0,
                }));
              }}
              className="h-4 w-4 accent-[#1f5f45]"
            />
            <span className="text-xs font-medium text-stone-700">Reinvestir proventos</span>
          </label>

          <details className="rounded-lg border border-stone-200 bg-white px-3 py-2 sm:col-span-2">
            <summary className="cursor-pointer text-xs font-semibold text-stone-700">Premissas variaveis por ano</summary>
            <div className="mt-3 grid gap-3 lg:grid-cols-3">
              <label className="block">
                <span className="text-xs font-medium text-stone-700">Rentabilidade mensal</span>
                <input
                  className="field mt-1"
                  type="text"
                  value={seriesText.variable_monthly_returns}
                  placeholder="1; 0,8; 0,6"
                  onChange={(event) => updateSeries("variable_monthly_returns", event.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-stone-700">Yield anual de proventos</span>
                <input
                  className="field mt-1"
                  type="text"
                  value={seriesText.variable_annual_dividend_yields}
                  placeholder="7,5; 8; 6"
                  onChange={(event) => updateSeries("variable_annual_dividend_yields", event.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-stone-700">Inflacao anual</span>
                <input
                  className="field mt-1"
                  type="text"
                  value={seriesText.variable_annual_inflation}
                  placeholder="4; 5; 4,5"
                  onChange={(event) => updateSeries("variable_annual_inflation", event.target.value)}
                />
              </label>
            </div>
          </details>

          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[0.7rem] leading-4 text-amber-700 sm:col-span-2">
            Capital gain, renda passiva, proventos reinvestidos e inflacao sao calculados separadamente no motor financeiro.
          </div>

          <div className="flex flex-wrap gap-3 sm:col-span-2">
            <button className="btn-primary h-11 min-w-40 flex-1 px-4 text-sm">
              <Calculator size={17} />
              {loading ? "Calculando" : "Simular"}
            </button>
            <button type="button" onClick={saveCurrentPremises} className="btn-secondary h-11 min-w-36 px-4 text-sm" title="Salvar premissas da simulacao">
              <Save size={17} />
              {saving ? "Salvando" : "Salvar"}
            </button>
            <button
              type="button"
              onClick={resetPremises}
              className="icon-button"
              title="Restaurar premissas"
            >
              <RotateCcw size={17} />
            </button>
          </div>
          {saveStatus ? <p className="text-xs font-semibold text-amber-700 sm:col-span-2">{saveStatus}</p> : null}
        </form>

        <div className="surface p-4">
          <h3 className="font-semibold text-stone-950">Patrimonio mes a mes</h3>
          <p className="text-xs text-stone-500">Serie anual resumida a partir dos meses simulados.</p>
          <div className="mt-3 h-[10.75rem]">
            {data ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.series} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
                  <CartesianGrid stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="year" tick={axisTick} />
                  <YAxis tickFormatter={(value) => compactCurrency.format(value)} tick={axisTick} />
                  <Tooltip formatter={(value) => currency.format(value)} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                  <Legend />
                  <Area type="monotone" dataKey="equity" name="Nominal" fill="var(--primary-soft)" stroke="var(--primary)" strokeWidth={2} />
                  <Area type="monotone" dataKey="realEquity" name="Real" fill="rgba(125, 196, 255, 0.12)" stroke="var(--info)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <LoadingState label="Preparando simulacao..." />
            )}
          </div>
        </div>
      </section>

      {error ? <ErrorState message={error} /> : null}

      {data ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Valor final projetado" value={currency.format(data.summary.finalValue)} hint="Valor nominal ao fim do prazo." icon={Goal} tone="amber" token={token} evidenceDomain="financial_projection" evidenceField="finalValue" />
            <StatCard label="Total aportado" value={currency.format(data.summary.totalContributed)} hint="Patrimonio inicial mais aportes mensais." icon={Calculator} tone="sky" token={token} evidenceDomain="financial_projection" evidenceField="totalContributed" />
            <StatCard label="Proventos acumulados" value={currency.format(data.summary.totalProceeds ?? data.summary.totalDividends)} hint="Dividendos, JCP, FIIs e outras distribuicoes no cenario." icon={Goal} tone="amber" token={token} evidenceDomain="financial_projection" evidenceField="totalProceeds" />
            <StatCard
              label="Tempo ate a meta"
              value={data.summary.estimatedYearsToGoal ? `${data.summary.estimatedYearsToGoal} anos` : "Nao atingida"}
              hint="Estimativa para renda passiva mensal informada."
              icon={Goal}
              tone="emerald"
              token={token}
              evidenceDomain="financial_projection"
              evidenceField="estimatedYearsToGoal"
            />
          </section>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Capital Gain" value={currency.format(data.breakdown?.capitalGain ?? data.summary.totalInterest)} hint="Valorizacao dos ativos, sem proventos." icon={Goal} tone="emerald" token={token} evidenceDomain="financial_projection" evidenceField="capitalGain" />
            <StatCard label="Renda passiva mensal" value={currency.format(data.independence?.monthlyPassiveIncome ?? 0)} hint="Calculada apenas por patrimonio vezes yield." icon={Goal} tone="amber" token={token} evidenceDomain="financial_projection" evidenceField="monthlyPassiveIncome" />
            <StatCard label="Retorno total" value={currency.format(data.breakdown?.totalReturn ?? 0)} hint="Capital gain mais distribuições." icon={Calculator} tone="sky" />
            <StatCard label="Patrimonio real" value={currency.format(data.breakdown?.finalReal ?? data.summary.finalValue)} hint="Valor descontado pela inflação." icon={Goal} tone="emerald" />
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="surface p-4">
              <h3 className="font-semibold text-stone-950">Como o patrimonio cresceu</h3>
              <p className="text-xs text-stone-500">Origem do patrimonio no cenario simulado.</p>
              <div className="mt-3 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.growthSources || []} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
                    <CartesianGrid stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="name" tick={axisTick} />
                    <YAxis tickFormatter={(value) => compactCurrency.format(value)} tick={axisTick} />
                    <Tooltip formatter={(value) => currency.format(value)} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                    <Bar dataKey="value" name="Valor" fill="var(--primary)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="surface p-4">
              <h3 className="font-semibold text-stone-950">Independencia financeira</h3>
              <div className="mt-3 grid gap-3 text-sm">
                <div className="flex justify-between gap-3 border-b border-stone-800 pb-2">
                  <span className="text-stone-500">Meta mensal</span>
                  <strong className="text-stone-950">{currency.format(data.independence?.monthlyGoal ?? 0)}</strong>
                </div>
                <div className="flex justify-between gap-3 border-b border-stone-800 pb-2">
                  <span className="text-stone-500">Patrimonio atual considerado</span>
                  <strong className="text-stone-950">{currency.format(data.independence?.currentWealthForGoal ?? form.initial_wealth ?? 0)}</strong>
                </div>
                <div className="flex justify-between gap-3 border-b border-stone-800 pb-2">
                  <span className="text-stone-500">Percentual da meta</span>
                  <strong className="text-stone-950">{data.independence?.currentGoalProgressPct ?? data.independence?.goalProgressPct ?? 0}% hoje</strong>
                </div>
                <div className="flex justify-between gap-3 border-b border-stone-800 pb-2">
                  <span className="text-stone-500">Quanto falta em patrimonio</span>
                  <strong className="text-stone-950">{data.independence?.remainingWealthToGoal != null ? currency.format(data.independence.remainingWealthToGoal) : "Sem yield"}</strong>
                </div>
                <div className="flex justify-between gap-3 border-b border-stone-800 pb-2">
                  <span className="text-stone-500">Patrimonio necessario</span>
                  <strong className="text-stone-950">{data.independence?.requiredWealth ? currency.format(data.independence.requiredWealth) : "Sem yield"}</strong>
                </div>
                <div className="flex justify-between gap-3 border-b border-stone-800 pb-2">
                  <span className="text-stone-500">Tempo estimado</span>
                  <strong className="text-stone-950">{data.independence?.estimatedYearsToGoal ? `${data.independence.estimatedYearsToGoal} anos` : "Nao atingida"}</strong>
                </div>
                <div className="flex justify-between gap-3 border-b border-stone-800 pb-2">
                  <span className="text-stone-500">Cenario no fim do prazo</span>
                  <strong className="text-stone-950">{data.independence?.projectedGoalProgressPct ?? 0}% da meta</strong>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-stone-500">Yield utilizado</span>
                  <strong className="text-stone-950">{data.independence?.yieldUsedAnnualPct ?? 0}% a.a.</strong>
                </div>
              </div>
            </div>
          </section>

          <section className="surface p-3">
            <h3 className="font-semibold text-stone-950">Leitura do cenario</h3>
            <p className="mt-1 text-xs leading-5 text-stone-600">{data.intelligentReading?.description}</p>
            <p className="mt-2 text-xs leading-5 text-stone-600">
              Retorno mensal efetivo considerado: {data.assumptions.effectiveMonthlyReturnPct}%.
              Yield mensal de proventos: {data.assumptions.monthlyDividendYieldPct}%.
              Reinvestimento de proventos: {data.assumptions.dividendReinvestmentRatePct ?? 0}%.
            </p>
            <p className="mt-1 text-[0.7rem] leading-4 text-stone-500">{data.disclaimer}</p>
          </section>
        </>
      ) : null}
    </div>
  );
}
