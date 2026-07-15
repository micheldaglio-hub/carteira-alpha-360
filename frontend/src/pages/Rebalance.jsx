import { AlertTriangle, Scale, Target } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import StatCard from "../components/StatCard.jsx";
import { apiFetch } from "../lib/api.js";
import { currency, pct } from "../lib/format.js";

const axisTick = { fontSize: 11, fill: "var(--muted)" };
const tooltipStyle = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)" };
const tooltipLabelStyle = { color: "var(--primary)" };

export default function Rebalance({ token }) {
  const [contribution, setContribution] = useState(2500);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = () => {
    setError("");
    apiFetch(`/rebalance?next_contribution=${contribution}`, { token }).then(setData).catch((err) => setError(err.message));
  };

  useEffect(() => {
    load();
  }, [token]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  const chartData = data.targets.map((item) => ({
    ticker: item.ticker,
    Atual: item.current,
    Ideal: item.ideal,
  }));

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Rebalanceamento inteligente</p>
          <h2 className="text-2xl font-semibold text-stone-950">Alocação atual versus ideal</h2>
        </div>
        <div className="flex gap-2">
          <input className="field h-10 w-40" type="number" value={contribution} onChange={(event) => setContribution(Number(event.target.value))} />
          <button onClick={load} className="btn-primary h-10 px-4 text-sm">
            <Scale size={16} />
            Calcular
          </button>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <StatCard label="Perfil" value={data.profile} hint="Perfil usado nas metas cadastradas." icon={Target} tone="amber" />
        <StatCard label="Próximo aporte" value={currency.format(data.nextContribution)} hint="Base para sugestão de distribuição." icon={Scale} tone="sky" />
        <StatCard label="Risco de concentração" value={data.concentrationRisk} hint={data.concentrationNotes[0] || "Sem ativo acima da faixa de atenção."} icon={AlertTriangle} tone={data.concentrationRisk === "alto" ? "amber" : "emerald"} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="surface p-4">
          <h3 className="font-semibold text-stone-950">Diferença de alocação</h3>
          <p className="text-xs text-stone-500">Atual e ideal por ativo.</p>
          <div className="mt-4 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="ticker" tick={axisTick} />
                <YAxis tickFormatter={(value) => `${value}%`} tick={axisTick} />
                <Tooltip formatter={(value) => pct(value)} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                <Legend />
                <Bar dataKey="Atual" fill="var(--success)" radius={[6, 6, 0, 0]} />
                <Bar dataKey="Ideal" fill="var(--primary)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="surface overflow-hidden">
          <div className="border-b border-stone-200 px-4 py-3">
            <h3 className="font-semibold text-stone-950">Sugestão de próximo aporte</h3>
            <p className="text-xs text-stone-500">Distribuição calculada apenas para aproximar pesos.</p>
          </div>
          <div className="divide-y divide-stone-100">
            {data.suggestions.length ? (
              data.suggestions.map((suggestion) => (
                <div key={suggestion.ticker} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div>
                    <p className="font-semibold text-stone-950">{suggestion.ticker}</p>
                    <p className="text-xs text-stone-500">{suggestion.reason}</p>
                  </div>
                  <p className="font-semibold text-amber-700">{currency.format(suggestion.suggestedAmount)}</p>
                </div>
              ))
            ) : (
              <p className="px-4 py-5 text-sm text-stone-500">Carteira alinhada com as metas atuais.</p>
            )}
          </div>
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-stone-50 text-xs uppercase text-stone-500">
              <tr>
                {["Ativo", "Atual", "Ideal", "Diferença", "Status"].map((head) => (
                  <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {data.targets.map((target) => (
                <tr key={target.ticker} className="hover:bg-stone-50">
                  <td className="px-4 py-3 font-semibold">{target.ticker}</td>
                  <td className="px-4 py-3">{pct(target.current)}</td>
                  <td className="px-4 py-3">{pct(target.ideal)}</td>
                  <td className="px-4 py-3">{pct(target.difference)}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-lg border border-stone-200 bg-stone-100 px-2.5 py-1.5 text-xs font-semibold text-stone-700">{target.status.replaceAll("_", " ")}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
