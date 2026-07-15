import { Activity, AlertTriangle, Banknote, Gauge, RefreshCw, ShieldAlert, TrendingDown } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import StatCard from "../components/StatCard.jsx";
import { apiFetch } from "../lib/api.js";
import { currency, pct } from "../lib/format.js";

const axisTick = { fontSize: 11, fill: "var(--muted)" };
const tooltipStyle = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)" };

function severityClass(severity) {
  if (severity === "critica") return "border-rose-400/40 bg-rose-500/10 text-rose-200";
  if (severity === "alta") return "border-amber-400/40 bg-amber-500/10 text-amber-200";
  if (severity === "media") return "border-sky-400/40 bg-sky-500/10 text-sky-200";
  return "border-emerald-400/40 bg-emerald-500/10 text-emerald-200";
}

export default function StressTest({ token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const payload = await apiFetch("/wealth-os/stress-test", { token });
      setData(payload);
      setSelectedId(payload.worstScenarioId || payload.scenarios?.[0]?.id || "");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const selected = useMemo(
    () => data?.scenarios?.find((item) => item.id === selectedId) || data?.scenarios?.[0],
    [data, selectedId]
  );

  if (error) return <ErrorState message={error} />;
  if (!data && loading) return <LoadingState label="Calculando stress test..." />;
  if (!data) return <LoadingState label="Carregando stress test..." />;

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Scenario & Stress Test</p>
          <h2 className="text-2xl font-semibold text-stone-950">Teste de resistencia da carteira</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
            Simula crise, queda de bolsa, Selic alta, dolar forte, cripto despencando e reducao de renda passiva.
            Sao choques deterministicos, nao previsoes de mercado.
          </p>
        </div>
        <button type="button" className="btn-primary h-10 px-4 text-sm" onClick={load} disabled={loading}>
          <RefreshCw size={16} />
          {loading ? "Atualizando" : "Atualizar"}
        </button>
      </header>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Score de resiliencia" value={`${Number(data.resilienceScore || 0).toFixed(0)}/100`} hint={String(data.riskLevel || "").replaceAll("_", " ")} icon={Gauge} tone={(data.resilienceScore || 0) >= 60 ? "emerald" : "rose"} compact token={token} evidenceDomain="stress_test" evidenceField="resilienceScore" />
        <StatCard label="Patrimonio base" value={currency.format(data.baseEquity || 0)} hint="Valor antes dos choques." icon={Activity} tone="amber" compact token={token} evidenceDomain="stress_test" evidenceField="baseEquity" />
        <StatCard label="Pior impacto" value={currency.format(data.worstImpactValue || 0)} hint={pct(data.worstImpactPct || 0)} icon={TrendingDown} tone="rose" compact token={token} evidenceDomain="stress_test" evidenceField="worstImpactValue" />
        <StatCard label="Renda passiva base" value={currency.format(data.basePassiveIncome || 0)} hint="Estimativa mensal antes do stress." icon={Banknote} tone="sky" compact token={token} evidenceDomain="stress_test" evidenceField="basePassiveIncome" />
        <StatCard label="Cenarios" value={`${data.scenarios?.length || 0}`} hint="Choques simulados no backend." icon={ShieldAlert} tone="stone" compact />
      </section>

      <section className="surface overflow-hidden">
        <div className="grid gap-4 border-b border-stone-200 p-4 xl:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)]">
          <div>
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} className="text-amber-500" />
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Leitura principal</p>
            </div>
            <h3 className="mt-2 text-xl font-semibold text-stone-950">{data.headline}</h3>
            <p className="mt-2 text-sm leading-6 text-stone-500">Pior cenário: {data.worstScenarioId}. Atualizado em {new Date(data.updatedAt).toLocaleString("pt-BR")}.</p>
            <div className="mt-3 grid gap-2">
              {(data.macroContext || []).slice(0, 5).map((item) => (
                <p key={item} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">{item}</p>
              ))}
            </div>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.scenarios || []} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="title" tick={axisTick} interval={0} angle={-18} textAnchor="end" height={84} />
                <YAxis tickFormatter={(value) => `${value}%`} tick={axisTick} width={50} />
                <Tooltip formatter={(value, name) => (name === "impactPct" ? pct(value) : currency.format(value))} contentStyle={tooltipStyle} />
                <Bar dataKey="impactPct" name="Impacto %" radius={[6, 6, 0, 0]}>
                  {(data.scenarios || []).map((item) => (
                    <Cell key={item.id} fill={(item.impactPct || 0) >= 0 ? "#3bd19f" : "#f97373"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid gap-4 p-4 xl:grid-cols-[minmax(20rem,0.8fr)_minmax(0,1.2fr)]">
          <div className="grid gap-2">
            {(data.scenarios || []).map((scenario) => (
              <button
                key={scenario.id}
                type="button"
                onClick={() => setSelectedId(scenario.id)}
                className={`rounded-lg border p-3 text-left transition ${selected?.id === scenario.id ? "border-amber-400/50 bg-amber-500/10" : "border-stone-200 bg-black/10 hover:border-amber-500/35"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-stone-950">{scenario.title}</p>
                    <p className="mt-1 text-xs text-stone-500">{scenario.category}</p>
                  </div>
                  <span className={`rounded-lg border px-2 py-1 text-[0.68rem] font-semibold uppercase ${severityClass(scenario.severity)}`}>
                    {scenario.severity}
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between gap-3 text-xs">
                  <span className={(scenario.impactValue || 0) < 0 ? "font-semibold text-rose-300" : "font-semibold text-emerald-300"}>{currency.format(scenario.impactValue || 0)}</span>
                  <span className="text-stone-500">{pct(scenario.impactPct || 0)}</span>
                </div>
              </button>
            ))}
          </div>

          {selected ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-stone-200 bg-stone-50 p-4">
                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">{selected.category}</p>
                    <h3 className="mt-1 text-xl font-semibold text-stone-950">{selected.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-stone-500">{selected.description}</p>
                  </div>
                  <span className={`rounded-lg border px-3 py-1 text-xs font-semibold uppercase ${severityClass(selected.severity)}`}>{selected.severity}</span>
                </div>
                <p className="mt-3 rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-200">{selected.reading}</p>
                <div className="mt-3 grid gap-3 md:grid-cols-4">
                  <div>
                    <p className="text-xs text-stone-500">Antes</p>
                    <p className="mt-1 text-base font-semibold text-stone-950">{currency.format(selected.shockedEquity || 0)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-stone-500">Depois</p>
                    <p className="mt-1 text-base font-semibold text-stone-950">{currency.format(selected.stressedEquity || 0)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-stone-500">Renda antes</p>
                    <p className="mt-1 text-base font-semibold text-stone-950">{currency.format(selected.passiveIncomeBefore || 0)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-stone-500">Renda depois</p>
                    <p className="mt-1 text-base font-semibold text-stone-950">{currency.format(selected.passiveIncomeAfter || 0)}</p>
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto rounded-lg border border-stone-200">
                <table className="premium-table min-w-full text-left text-sm">
                  <thead>
                    <tr>
                      <th>Classe</th>
                      <th>Antes</th>
                      <th>Choque</th>
                      <th>Impacto</th>
                      <th>Depois</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selected.bucketImpacts || []).map((bucket) => (
                      <tr key={bucket.bucket}>
                        <td className="font-semibold">{bucket.bucket}</td>
                        <td>{currency.format(bucket.before || 0)}</td>
                        <td className={(bucket.shockPct || 0) < 0 ? "text-rose-300" : "text-emerald-300"}>{pct(bucket.shockPct || 0)}</td>
                        <td className={(bucket.impactValue || 0) < 0 ? "text-rose-300" : "text-emerald-300"}>{currency.format(bucket.impactValue || 0)}</td>
                        <td>{currency.format(bucket.after || 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Acoes de acompanhamento</p>
                  <div className="mt-3 space-y-2">
                    {(selected.recommendedActions || []).map((item) => (
                      <p key={item} className="text-xs leading-5 text-stone-500">{item}</p>
                    ))}
                  </div>
                </div>
                <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Premissas</p>
                  <div className="mt-3 space-y-2">
                    {(selected.assumptions || []).map((item) => (
                      <p key={item} className="text-xs leading-5 text-stone-500">{item}</p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </section>

      <section className="surface p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Premissas gerais do motor</p>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {(data.assumptions || []).map((item) => (
            <p key={item} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">{item}</p>
          ))}
        </div>
      </section>
    </div>
  );
}
