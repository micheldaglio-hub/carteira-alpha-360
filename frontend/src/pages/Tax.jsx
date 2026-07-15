import { AlertTriangle, Calculator, FileText, RefreshCw, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import StatCard from "../components/StatCard.jsx";
import { apiFetch } from "../lib/api.js";
import { currency } from "../lib/format.js";

const currentYear = new Date().getFullYear();
const currentMonth = new Date().getMonth() + 1;

export default function Tax({ token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ year: currentYear, month: currentMonth });
  const [loading, setLoading] = useState(false);

  const params = useMemo(() => new URLSearchParams({ year: String(filters.year), month: String(filters.month) }), [filters]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    apiFetch(`/wealth-os/tax?${params.toString()}`, { token })
      .then((payload) => {
        if (active) setData(payload);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [params, token]);

  if (error) return <ErrorState message={error} />;
  if (!data && loading) return <LoadingState />;

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Impostos</p>
          <h2 className="text-2xl font-semibold text-stone-950">Tax Engine</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
            Estimativa operacional de IRRF, DARF e lacunas tributarias. Nao substitui contador nem declaracao oficial.
          </p>
        </div>
        <div className="surface flex flex-wrap items-end gap-3 p-3">
          <label className="block">
            <span className="text-xs font-medium text-stone-700">Ano</span>
            <input className="field mt-1 h-9 w-24" type="number" value={filters.year} onChange={(event) => setFilters((current) => ({ ...current, year: Number(event.target.value) }))} />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-stone-700">Mes</span>
            <input className="field mt-1 h-9 w-20" type="number" min="1" max="12" value={filters.month} onChange={(event) => setFilters((current) => ({ ...current, month: Number(event.target.value) }))} />
          </label>
          <button type="button" className="btn-primary h-9 px-3 text-xs" onClick={() => setFilters((current) => ({ ...current }))}>
            <RefreshCw size={15} />
            Atualizar
          </button>
        </div>
      </header>

      {data ? (
        <>
          <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <StatCard label="Proventos brutos" value={currency.format(data.grossIncome || 0)} hint={data.period} icon={FileText} tone="amber" compact token={token} evidenceDomain="tax" evidenceField="grossIncome" />
            <StatCard label="Ganho realizado" value={currency.format(data.realizedGain || 0)} hint="Base operacional do periodo." icon={Calculator} tone={(data.realizedGain || 0) >= 0 ? "emerald" : "rose"} compact token={token} evidenceDomain="tax" evidenceField="realizedGain" />
            <StatCard label="IRRF estimado" value={currency.format(data.estimatedWithheldTax || 0)} hint="Principalmente JCP." icon={ShieldAlert} tone="rose" compact token={token} evidenceDomain="tax" evidenceField="estimatedWithheldTax" />
            <StatCard label="DARF estimado" value={currency.format(data.estimatedTaxDue || 0)} hint="Ganho de capital estimado." icon={AlertTriangle} tone={(data.estimatedTaxDue || 0) > 0 ? "rose" : "emerald"} compact token={token} evidenceDomain="tax" evidenceField="estimatedTaxDue" />
            <StatCard label="Liquido estimado" value={currency.format(data.netIncomeAfterEstimatedTax || 0)} hint="Proventos + ganhos - impostos estimados." icon={Calculator} tone="sky" compact token={token} evidenceDomain="tax" evidenceField="netIncomeAfterEstimatedTax" />
          </section>

          <section className="surface p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-stone-950">Leitura tributaria</h3>
                <p className="mt-1 text-sm leading-6 text-stone-500">{data.headline}</p>
              </div>
              <span className="rounded-lg border border-amber-500/35 bg-amber-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-amber-700">
                {data.status}
              </span>
            </div>
            {data.alerts?.length ? (
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {data.alerts.map((item) => (
                  <p key={item} className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-200">
                    {item}
                  </p>
                ))}
              </div>
            ) : null}
          </section>

          <section className="surface overflow-hidden">
            <div className="border-b border-stone-800 p-4">
              <h3 className="text-base font-semibold text-stone-950">Eventos tributarios</h3>
              <p className="text-xs text-stone-500">Separacao entre renda, IRRF, ganho de capital e revisoes.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="premium-table min-w-full text-left text-sm">
                <thead>
                  <tr>
                    <th>Categoria</th>
                    <th>Classe</th>
                    <th>Bruto</th>
                    <th>Base</th>
                    <th>Aliquota</th>
                    <th>Imposto</th>
                    <th>Liquido</th>
                    <th>Leitura</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.items || []).map((item) => (
                    <tr key={item.id}>
                      <td className="font-semibold">{item.category}</td>
                      <td>{item.assetClass}</td>
                      <td>{currency.format(item.grossAmount || 0)}</td>
                      <td>{currency.format(item.taxableAmount || 0)}</td>
                      <td>{Number(item.rate || 0).toFixed(2)}%</td>
                      <td>{currency.format(item.estimatedTax || 0)}</td>
                      <td>{currency.format(item.netAmount || 0)}</td>
                      <td className="max-w-xl text-xs leading-5 text-stone-500">{item.reading}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="grid gap-4 xl:grid-cols-2">
            <div className="surface p-4">
              <h3 className="text-base font-semibold text-stone-950">Regras usadas</h3>
              <div className="mt-3 space-y-2">
                {(data.rules || []).map((rule) => (
                  <div key={rule.id} className="rounded-lg border border-stone-800 bg-black/10 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand">{rule.title}</p>
                      <span className="text-xs text-stone-500">{rule.rate ?? "N/D"}%</span>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-stone-500">{rule.summary}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="surface p-4">
              <h3 className="text-base font-semibold text-stone-950">Lacunas controladas</h3>
              <div className="mt-3 space-y-2">
                {(data.dataGaps || []).map((gap) => (
                  <p key={gap} className="rounded-lg border border-stone-800 bg-black/10 px-3 py-2 text-xs leading-5 text-stone-500">
                    {gap}
                  </p>
                ))}
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
