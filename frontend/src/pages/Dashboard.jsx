import { Activity, Banknote, Brain, Coins, Compass, LineChart, PiggyBank, Save, ShieldCheck, Sparkles, Target, TrendingUp, Wallet } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import StatCard from "../components/StatCard.jsx";
import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import { apiFetch } from "../lib/api.js";
import { compactCurrency, currency, pct } from "../lib/format.js";

const colors = ["var(--primary)", "var(--success)", "var(--info)", "#ff8a65", "#8f6fe8", "var(--muted)"];
const axisTick = { fontSize: 11, fill: "var(--muted)" };
const tooltipStyle = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)" };
const allocationTooltipStyle = {
  background: "var(--surface-4)",
  border: "1px solid var(--border-strong)",
  borderRadius: 8,
  boxShadow: "var(--shadow-5)",
  color: "var(--text)",
  padding: "0.55rem 0.7rem",
};
const tooltipLabelStyle = { color: "var(--primary)" };
const tooltipItemStyle = { color: "var(--text)", fontWeight: 700 };
const DASHBOARD_PROJECTION_STORAGE_KEY = "carteira-alpha-dashboard-projection-premises-v1";
const dashboardProjectionDefaults = { monthlyContribution: 100, monthlyReturn: 1 };
const normalizeDashboardProjectionPremises = (premises) => ({
  monthlyContribution: Number(premises?.monthly_contribution ?? premises?.monthlyContribution ?? dashboardProjectionDefaults.monthlyContribution),
  monthlyReturn: Number(premises?.monthly_return ?? premises?.monthlyReturn ?? dashboardProjectionDefaults.monthlyReturn),
});
const readDashboardProjectionPremises = () => {
  try {
    const raw = localStorage.getItem(DASHBOARD_PROJECTION_STORAGE_KEY);
    return raw ? normalizeDashboardProjectionPremises(JSON.parse(raw)) : dashboardProjectionDefaults;
  } catch {
    return dashboardProjectionDefaults;
  }
};
const writeDashboardProjectionPremises = (premises) => {
  try {
    localStorage.setItem(DASHBOARD_PROJECTION_STORAGE_KEY, JSON.stringify(premises));
  } catch {
    // Browser storage can be unavailable in restricted contexts.
  }
};
const buildCommandFallback = (metrics, intelligence) => {
  const total = Number(metrics?.totalEquity || 0);
  const passiveGoal = 20000;
  const firstMilestone = 100000;
  const firstMillion = 1000000;
  const passiveIncome = Number(metrics?.projectedPassiveIncome || 0);
  const progress = (target) => Math.min(100, Math.max(0, total / target * 100));
  return {
    greeting: intelligence?.greeting || "",
    mission: "Missão atual: manter o centro de comando ativo enquanto os motores sincronizam.",
    headline: "Fallback operacional com patrimônio, metas e confiabilidade básica. A API completa será usada automaticamente quando responder.",
    wealthProgressScore: {
      score: Number(intelligence?.scoreAlpha || 0),
      status: "sincronizando",
    },
    topGoals: [
      {
        id: "fallback_100k",
        title: "Primeiros R$ 100 mil",
        progressPct: progress(firstMilestone),
        remainingValue: Math.max(0, firstMilestone - total),
      },
      {
        id: "fallback_1m",
        title: "Primeiro R$ 1 milhao",
        progressPct: progress(firstMillion),
        remainingValue: Math.max(0, firstMillion - total),
      },
      {
        id: "fallback_income",
        title: "Renda passiva mensal",
        progressPct: Math.min(100, Math.max(0, passiveIncome / passiveGoal * 100)),
        remainingValue: Math.max(0, passiveGoal - passiveIncome),
      },
    ],
    opportunities: [
      {
        id: "fallback_sync",
        title: "Centro de comando sincronizando",
        priority: "media",
        thesis: "Os dados principais carregaram. O Wealth OS completo sera exibido quando a API auxiliar concluir sem erro.",
      },
    ],
    dataConfidence: [
      { area: "Dashboard", confidenceScore: 100 },
      { area: "Centro de comando", confidenceScore: 55 },
      { area: "Cache local", confidenceScore: 75 },
    ],
  };
};

function AllocationTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="allocation-pie-tooltip">
      <div className="flex items-center gap-2">
        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
        <span className="allocation-pie-tooltip__name">{item.name}</span>
      </div>
      <strong className="allocation-pie-tooltip__value">{currency.format(item.value || 0)}</strong>
    </div>
  );
}

export default function Dashboard({ token }) {
  const [data, setData] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [intelligenceLoaded, setIntelligenceLoaded] = useState(false);
  const [commandCenter, setCommandCenter] = useState(null);
  const [commandCenterLoaded, setCommandCenterLoaded] = useState(false);
  const [projectionScenario, setProjectionScenario] = useState(() => readDashboardProjectionPremises());
  const [dashboardProjection, setDashboardProjection] = useState(null);
  const [error, setError] = useState("");
  const [projectionSaving, setProjectionSaving] = useState(false);
  const [projectionSaveStatus, setProjectionSaveStatus] = useState("");

  useEffect(() => {
    let active = true;
    setError("");
    setData(null);
    setIntelligence(null);
    setIntelligenceLoaded(false);
    setCommandCenter(null);
    setCommandCenterLoaded(false);
    setDashboardProjection(null);

    apiFetch("/dashboard", { token })
      .then((payload) => {
        if (active) setData(payload);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });

    apiFetch("/intelligence/summary", { token })
      .then((payload) => {
        if (active) setIntelligence(payload);
      })
      .catch(() => {
        if (active) setIntelligence(null);
      })
      .finally(() => {
        if (active) setIntelligenceLoaded(true);
      });

    apiFetch("/wealth-os/command-center", { token })
      .then((payload) => {
        if (active) setCommandCenter(payload);
      })
      .catch(() => {
        if (active) setCommandCenter(null);
      })
      .finally(() => {
        if (active) setCommandCenterLoaded(true);
      });

    apiFetch("/dashboard/projection-premises", { token })
      .then((payload) => {
        if (!active || !payload.premises) return;
        const saved = normalizeDashboardProjectionPremises(payload.premises);
        setProjectionScenario(saved);
        writeDashboardProjectionPremises(saved);
        setProjectionSaveStatus("Premissas salvas carregadas");
      })
      .catch(() => {
        if (active) {
          const localPremises = readDashboardProjectionPremises();
          setProjectionScenario(localPremises);
          if (localPremises.monthlyContribution !== dashboardProjectionDefaults.monthlyContribution || localPremises.monthlyReturn !== dashboardProjectionDefaults.monthlyReturn) {
            setProjectionSaveStatus("Premissas locais carregadas");
          }
        }
      });

    return () => {
      active = false;
    };
  }, [token]);

  const updateProjectionScenario = (key, value) => {
    setProjectionSaveStatus("");
    setProjectionScenario((current) => ({ ...current, [key]: value }));
  };

  const saveProjectionScenario = async () => {
    setProjectionSaving(true);
    setError("");
    const payload = {
      monthly_contribution: Number(projectionScenario.monthlyContribution || 0),
      monthly_return: Number(projectionScenario.monthlyReturn || 0),
    };
    try {
      const result = await apiFetch("/dashboard/projection-premises", { method: "PUT", token, body: payload });
      const saved = normalizeDashboardProjectionPremises(result.premises || payload);
      setProjectionScenario(saved);
      writeDashboardProjectionPremises(saved);
      setProjectionSaveStatus("Premissas salvas");
    } catch (err) {
      writeDashboardProjectionPremises(projectionScenario);
      setProjectionSaveStatus("Salvo neste navegador");
    } finally {
      setProjectionSaving(false);
    }
  };

  useEffect(() => {
    if (!data) return undefined;
    let active = true;
    const metrics = data.metrics;
    const basePayload = {
      initial_wealth: metrics.totalEquity || 0,
      monthly_contribution: Number(projectionScenario.monthlyContribution || 0),
      expected_monthly_return: Number(projectionScenario.monthlyReturn || 0),
      expected_annual_dividend_yield: 0,
      reinvest_dividends: false,
      annual_inflation: 0,
      passive_income_goal: 0,
    };

    Promise.all([
      apiFetch("/projections/simulate", { method: "POST", token, body: { ...basePayload, years: 10 } }),
      apiFetch("/projections/simulate", { method: "POST", token, body: { ...basePayload, years: 30 } }),
    ])
      .then(([ten, thirty]) => {
        if (active) {
          setDashboardProjection({ ten: ten.summary.finalValue, thirty: thirty.summary.finalValue });
        }
      })
      .catch(() => {
        if (active) setDashboardProjection(null);
      });

    return () => {
      active = false;
    };
  }, [data, projectionScenario.monthlyContribution, projectionScenario.monthlyReturn, token]);

  if (error) return <ErrorState message={error} />;
  if (!data || !intelligenceLoaded || !commandCenterLoaded) return <LoadingState />;

  const metrics = data.metrics;
  const positive = metrics.pnl >= 0;
  const tradingDesk = data.externalIntegrations?.tradingDesk;
  const tradingDeskConnected = Boolean(tradingDesk?.connected);
  const tradingDeskVisible = Boolean(tradingDesk);
  const tradingDeskStatusMessage = (() => {
    if (tradingDeskConnected) {
      if (tradingDesk.initialCapital > 0) {
        return `P/L ${currency.format(tradingDesk.totalPnl)} sobre capital de ${currency.format(tradingDesk.initialCapital)}.`;
      }
      return `P/L ${currency.format(tradingDesk.totalPnl)}.`;
    }
    if (tradingDesk?.status === "disabled") {
      return "Integração não configurada neste ambiente.";
    }
    return tradingDesk?.message || "Integração configurada, mas sem resposta agora.";
  })();
  const wealthCommand = commandCenter || intelligence?.commandCenter || buildCommandFallback(metrics, intelligence);

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Visão geral</p>
          <h2 className="text-2xl font-semibold text-stone-950">Painel institucional da carteira</h2>
        </div>
        <p className="max-w-2xl text-sm leading-6 text-stone-500">
          Métricas calculadas sobre posições, proventos e snapshots de mercado. Projeções são cenários ajustáveis, não promessa de resultado.
        </p>
      </header>

      {intelligence ? (
        <section className="surface overflow-hidden p-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-stretch xl:justify-between">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="brand-badge">
                  <Brain size={15} />
                </span>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Resumo Inteligente</p>
              </div>
              <h3 className="mt-2 text-lg font-semibold leading-snug text-stone-950 sm:text-xl">
                {intelligence.greeting} {intelligence.headline}
              </h3>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {intelligence.bullets?.slice(0, 4).map((item) => (
                  <div key={item} className="flex min-w-0 items-start gap-2 text-xs leading-5 text-stone-500">
                    <Sparkles size={14} className="mt-0.5 shrink-0 text-amber-700" />
                    <span className="min-w-0">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 divide-x divide-stone-800 border-t border-stone-800 pt-3 xl:w-[28rem] xl:border-l xl:border-t-0 xl:pl-4 xl:pt-0">
              <div className="px-3 py-1 xl:first:pl-0">
                <p className="text-xs uppercase tracking-[0.14em] text-stone-500">Eventos</p>
                <p className="mt-1 text-xl font-semibold text-stone-950">{intelligence.importantEventsCount}</p>
              </div>
              <div className="px-3 py-1">
                <p className="text-xs uppercase tracking-[0.14em] text-stone-500">Score Alpha</p>
                <p className="mt-1 text-xl font-semibold text-amber-700">{Math.round(intelligence.scoreAlpha)}</p>
              </div>
              <div className="px-3 py-1 xl:last:pr-0">
                <p className="text-xs uppercase tracking-[0.14em] text-stone-500">Proventos mes</p>
                <p className="mt-1 text-xl font-semibold text-stone-950">{currency.format(intelligence.dividendsMonth)}</p>
              </div>
            </div>
          </div>
          {intelligence.attention ? (
            <div className="mt-3 border-t border-stone-800 pt-2 text-xs font-medium text-amber-700">
              {intelligence.attention}
            </div>
          ) : null}
        </section>
      ) : null}

      {wealthCommand ? (
        <section className="grid gap-3 xl:grid-cols-[1.08fr_0.92fr]">
          <div className="surface p-3">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="brand-badge">
                    <Compass size={15} />
                  </span>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Centro de Comando Patrimonial</p>
                </div>
                <h3 className="mt-2 text-base font-semibold leading-snug text-stone-950 sm:text-lg">
                  {wealthCommand.greeting} {wealthCommand.mission}
                </h3>
                <p className="mt-1 text-xs leading-5 text-stone-500">{wealthCommand.headline}</p>
              </div>
              <div className="min-w-[8rem] rounded-lg border border-amber-500/35 bg-amber-500/10 p-3 text-right">
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-amber-700">Wealth Score</p>
                <p className="mt-1 text-2xl font-semibold text-amber-700">{Math.round(wealthCommand.wealthProgressScore?.score || 0)}</p>
                <p className="text-[0.68rem] text-stone-500">{wealthCommand.wealthProgressScore?.status || "em leitura"}</p>
              </div>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-3">
              {(wealthCommand.topGoals || []).slice(0, 3).map((goal) => (
                <div key={goal.id} className="rounded-lg border border-stone-800 bg-black/10 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold text-stone-950">{goal.title}</p>
                    <Target size={14} className="text-amber-700" />
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-stone-800">
                    <div className="h-full rounded-full bg-amber-400" style={{ width: `${Math.min(100, Math.max(0, goal.progressPct || 0))}%` }} />
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[0.68rem] text-stone-500">
                    <span>{pct(goal.progressPct || 0)}</span>
                    <span>faltam {currency.format(goal.remainingValue || 0)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="surface p-3">
            <div className="flex items-center gap-2">
              <span className="brand-badge">
                <ShieldCheck size={15} />
              </span>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Oportunidades e Confiança</p>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-1">
              {(wealthCommand.opportunities || []).slice(0, 2).map((item) => (
                <div key={item.id} className="rounded-lg border border-stone-800 bg-black/10 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold text-stone-950">{item.title}</p>
                    <span className="rounded-md border border-amber-500/35 px-2 py-0.5 text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-amber-700">{item.priority}</span>
                  </div>
                  <p className="mt-1 text-xs leading-5 text-stone-500">{item.thesis}</p>
                </div>
              ))}
              <div className="rounded-lg border border-stone-800 bg-black/10 p-3">
                <p className="text-xs font-semibold text-stone-950">Confiabilidade dos dados</p>
                <div className="mt-2 space-y-2">
                  {(wealthCommand.dataConfidence || []).slice(0, 3).map((item) => (
                    <div key={item.area} className="flex items-center justify-between gap-3 text-[0.68rem] text-stone-500">
                      <span>{item.area}</span>
                      <span className="font-semibold text-stone-950">{Math.round(item.confidenceScore || 0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      <section className={`grid gap-3 md:grid-cols-2 ${tradingDeskVisible ? "xl:grid-cols-5" : "xl:grid-cols-4"}`}>
        <StatCard
          label="Patrimônio total"
          value={currency.format(metrics.totalEquity)}
          hint={metrics.externalEquity > 0 ? `Inclui ${currency.format(metrics.externalEquity)} de integrações externas.` : "Valor atual estimado dos ativos."}
          icon={Wallet}
          tone="amber"
          compact
          token={token}
          evidenceDomain="dashboard"
          evidenceField="totalEquity"
        />
        <StatCard label="Valor investido" value={currency.format(metrics.investedValue)} hint="Preco medio ajustado por vendas e capital externo alocado." icon={PiggyBank} tone="sky" compact token={token} evidenceDomain="dashboard" evidenceField="investedValue" />
        <StatCard label="Proventos no ano" value={currency.format(metrics.proceedsYear ?? metrics.dividendsYear)} hint={`${currency.format(metrics.proceedsMonth ?? metrics.dividendsMonth)} recebidos no mes.`} icon={Coins} tone="amber" compact token={token} evidenceDomain="dashboard" evidenceField="proceedsYear" />
        <StatCard
          label="P/L total"
          value={currency.format(metrics.pnl)}
          hint={`${positive ? "Ganho" : "Perda"} de ${pct(metrics.pnlPct)} em ações, cripto e integrações.`}
          icon={Activity}
          tone={positive ? "emerald" : "rose"}
          compact
          token={token}
          evidenceDomain="dashboard"
          evidenceField="pnl"
        />
        {tradingDeskVisible ? (
          <StatCard
            label="Trading Desk EV+"
            value={tradingDeskConnected ? currency.format(tradingDesk.currentBalance) : "Indisponivel"}
            hint={tradingDeskStatusMessage}
            icon={LineChart}
            tone={tradingDeskConnected && tradingDesk.totalPnl >= 0 ? "emerald" : "rose"}
            compact
          />
        ) : null}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <div className="surface p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-stone-950">Evolucao patrimonial</h3>
              <p className="text-xs text-stone-500">Patrimônio estimado versus capital investido.</p>
            </div>
            <LineChart size={19} className="text-amber-700" />
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.history} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
                <defs>
                  <linearGradient id="equity" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.28} />
                    <stop offset="95%" stopColor="var(--primary)" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="month" tick={axisTick} />
                <YAxis tickFormatter={(value) => compactCurrency.format(value)} tick={axisTick} />
                <Tooltip
                  formatter={(value) => currency.format(value)}
                  contentStyle={allocationTooltipStyle}
                  labelStyle={tooltipLabelStyle}
                  itemStyle={tooltipItemStyle}
                  wrapperClassName="chart-tooltip-wrapper"
                />
                <Legend />
                <Area type="monotone" dataKey="equity" name="Patrimônio" stroke="var(--primary)" fill="url(#equity)" strokeWidth={2} />
                <Area type="monotone" dataKey="invested" name="Investido" stroke="var(--info)" fill="transparent" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="surface p-4">
          <h3 className="text-base font-semibold text-stone-950">Alocacao por classe</h3>
          <p className="text-xs text-stone-500">Peso atual por tipo de ativo.</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.allocations.byClass} dataKey="value" nameKey="name" innerRadius={58} outerRadius={96} paddingAngle={3}>
                  {data.allocations.byClass.map((entry, index) => (
                    <Cell key={entry.name} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip content={<AllocationTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="allocation-chart-legend">
            {data.allocations.byClass.map((entry, index) => (
              <div key={entry.name} className="allocation-chart-legend__item">
                <span className="allocation-chart-legend__dot" style={{ backgroundColor: colors[index % colors.length] }} />
                <span className="allocation-chart-legend__label">{entry.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="surface p-4">
          <h3 className="text-base font-semibold text-stone-950">Proventos recebidos</h3>
          <p className="text-xs text-stone-500">Dividendos, JCP e rendimentos de FIIs carregados no perfil.</p>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.dividendHistory} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="month" tick={axisTick} />
                <YAxis tickFormatter={(value) => compactCurrency.format(value)} tick={axisTick} />
                <Tooltip formatter={(value) => currency.format(value)} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                <Bar dataKey="proceeds" name="Proventos" fill="var(--primary)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="surface p-4 sm:col-span-2">
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-brand">Premissas das projeções</h3>
            <p className="mt-2 text-xs leading-5 text-stone-500">
              Usa seu patrimônio atual como ponto de partida. Ajuste aporte e retorno para o seu cenário.
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <label className="block">
                <span className="text-xs font-medium text-stone-700">Aporte mensal</span>
                <input
                  className="field mt-1 h-10"
                  type="number"
                  min="0"
                  step="50"
                  value={projectionScenario.monthlyContribution}
                  onChange={(event) => updateProjectionScenario("monthlyContribution", Number(event.target.value))}
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-stone-700">Rentabilidade mensal (%)</span>
                <input
                  className="field mt-1 h-10"
                  type="number"
                  step="0.1"
                  value={projectionScenario.monthlyReturn}
                  onChange={(event) => updateProjectionScenario("monthlyReturn", Number(event.target.value))}
                />
              </label>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button type="button" onClick={saveProjectionScenario} className="btn-secondary h-9 px-3 text-xs" title="Salvar premissas do relatório">
                <Save size={15} />
                {projectionSaving ? "Salvando" : "Salvar"}
              </button>
              {projectionSaveStatus ? <span className="text-xs font-semibold text-amber-700">{projectionSaveStatus}</span> : null}
            </div>
          </div>
          <StatCard
            label="Renda passiva projetada"
            value={currency.format(metrics.projectedPassiveIncome)}
            hint={`Mensal estimado: ${currency.format(metrics.projectedFixedIncome || 0)} em renda fixa/CDI + ${currency.format(metrics.projectedProceedsIncome || 0)} em proventos.`}
            icon={Banknote}
            tone="amber"
            token={token}
            evidenceDomain="dashboard"
            evidenceField="projectedPassiveIncome"
          />
          <StatCard label="Projeção em 10 anos" value={compactCurrency.format(dashboardProjection?.ten ?? metrics.projection10y)} hint="Cenário com as premissas informadas acima." icon={TrendingUp} tone="emerald" token={token} evidenceDomain="dashboard" evidenceField="projection10y" />
          <StatCard label="Projeção em 30 anos" value={compactCurrency.format(dashboardProjection?.thirty ?? metrics.projection30y)} hint="Resultado nominal do cenário informado acima." icon={TrendingUp} tone="sky" token={token} evidenceDomain="dashboard" evidenceField="projection30y" />
        </div>
      </section>
    </div>
  );
}
