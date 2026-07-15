import { Database } from "lucide-react";
import { useState } from "react";

import { apiFetch } from "../lib/api.js";

function EvidenceButton({ token, domain, fieldName }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState("");

  async function toggle() {
    const nextOpen = !open;
    setOpen(nextOpen);
    if (!nextOpen || payload || !token || !domain || !fieldName) return;
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ domain, field_name: fieldName, limit: "5" });
      const result = await apiFetch(`/ops/evidence?${params.toString()}`, { token });
      setPayload(result);
    } catch (err) {
      setError(err.message || "Nao foi possivel carregar a origem.");
    } finally {
      setLoading(false);
    }
  }

  if (!token || !domain || !fieldName) return null;
  const rows = payload?.evidence || [];

  return (
    <div className="relative">
      <button
        type="button"
        onClick={toggle}
        className="flex h-7 w-7 items-center justify-center rounded-lg border border-stone-700 bg-black/20 text-stone-400 transition hover:border-amber-500/70 hover:text-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-400/40"
        title="Ver origem do calculo"
      >
        <Database size={14} />
      </button>
      {open ? (
        <div className="absolute right-0 top-8 z-50 w-80 rounded-lg border border-stone-700 bg-[var(--surface-4)] p-3 text-left shadow-2xl">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-amber-300">Origem do calculo</p>
          {loading ? <p className="mt-2 text-xs text-stone-400">Carregando evidencias...</p> : null}
          {error ? <p className="mt-2 text-xs text-rose-300">{error}</p> : null}
          {!loading && !error && rows.length === 0 ? <p className="mt-2 text-xs text-stone-400">Ainda nao ha evidencia gravada para este campo.</p> : null}
          <div className="mt-2 space-y-2">
            {rows.slice(0, 3).map((row) => (
              <div key={row.id} className="rounded-md border border-stone-700 bg-black/20 p-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[0.68rem] font-semibold text-stone-100">{row.provider || row.sourceType}</span>
                  <span className="text-[0.68rem] font-semibold text-amber-300">{Math.round(row.confidence || 0)}%</span>
                </div>
                <p className="mt-1 text-[0.68rem] leading-4 text-stone-400">
                  {row.formulaName || row.sourceRef || "Fonte interna"} | {row.sourceType}
                </p>
                <p className="mt-1 text-[0.68rem] leading-4 text-stone-500">
                  {row.valueNumeric !== null && row.valueNumeric !== undefined ? `Valor registrado: ${Number(row.valueNumeric).toLocaleString("pt-BR")}` : "Evidencia textual registrada"}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function StatCard({ label, value, hint, icon: Icon, tone = "emerald", compact = false, token, evidenceDomain, evidenceField }) {
  const tones = {
    emerald: "border border-emerald-200 bg-emerald-50 text-emerald-700",
    sky: "border border-sky-200 bg-sky-50 text-sky-700",
    amber: "border border-amber-200 bg-amber-50 text-amber-700",
    rose: "border border-rose-200 bg-rose-50 text-rose-700",
    stone: "border border-stone-200 bg-stone-100 text-stone-700",
  };
  return (
    <div className={`surface ${compact ? "min-h-[5.65rem] p-2.5" : "min-h-[6.35rem] p-3"}`}>
      <div className="flex items-start justify-between gap-2">
        <p className={`${compact ? "text-[0.68rem] tracking-[0.1em]" : "text-xs tracking-[0.11em]"} font-semibold uppercase text-stone-500`}>{label}</p>
        <div className="flex items-center gap-1.5">
          <EvidenceButton token={token} domain={evidenceDomain} fieldName={evidenceField} />
          {Icon ? (
            <span className={`flex ${compact ? "h-7 w-7" : "h-8 w-8"} items-center justify-center rounded-lg ${tones[tone] || tones.emerald}`}>
              <Icon size={compact ? 14 : 16} />
            </span>
          ) : null}
        </div>
      </div>
      <p className={`${compact ? "mt-1.5 text-lg" : "mt-2 text-xl"} font-semibold leading-tight text-stone-950`}>{value}</p>
      <p className={`${compact ? "mt-0.5 text-[0.67rem] leading-3" : "mt-1 text-[0.72rem] leading-4"} text-stone-500`}>{hint}</p>
    </div>
  );
}
