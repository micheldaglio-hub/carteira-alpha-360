import { Activity, Bell, CheckCircle2, RefreshCw, ShieldAlert, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import StatCard from "../components/StatCard.jsx";
import { apiFetch } from "../lib/api.js";

const severity = {
  info: "border-sky-200 bg-sky-50 text-sky-800",
  opportunity: "border-emerald-200 bg-emerald-50 text-emerald-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  critical: "border-rose-200 bg-rose-50 text-rose-800",
};

const severityLabel = {
  info: "Informativo",
  opportunity: "Oportunidade",
  success: "Positivo",
  warning: "Atencao",
  critical: "Critico",
};

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR");
}

function sourceLabel(value) {
  const source = String(value || "").toLowerCase();
  if (source.includes("guardian")) return "Guardian";
  if (source.includes("insight")) return "Alpha Intelligence";
  if (source.includes("alpha")) return "Alpha Intelligence";
  if (source.includes("portfolio")) return "Carteira";
  if (source.includes("alerts")) return "Alerta manual";
  return "Alpha";
}

function statusLabel(value) {
  const status = String(value || "").toLowerCase();
  if (status === "aberto") return "Aberto";
  if (status === "lido") return "Lido";
  if (status === "resolvido") return "Resolvido";
  return status || "Monitorando";
}

export default function Alerts({ token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await apiFetch("/alerts", { token });
      setData(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = window.setInterval(load, 180000);
    return () => window.clearInterval(interval);
  }, [token]);

  async function markRead(alert) {
    if (alert.readOnly) return;
    await apiFetch(`/alerts/${alert.id}/read`, { method: "POST", token });
    await load();
  }

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  const summary = data.summary || {};
  const alerts = data.alerts || [];

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Alertas</p>
          <h2 className="text-2xl font-semibold text-stone-950">Monitoramento Alpha</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
            Eventos, pontos de atencao e leitura do Guardian sobre concentracao, score, renda, risco e saude da carteira.
          </p>
        </div>
        <button type="button" onClick={load} className="btn-secondary h-10 px-3 text-sm" disabled={loading}>
          <RefreshCw size={16} />
          {loading ? "Atualizando" : "Atualizar"}
        </button>
      </header>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Alertas abertos" value={summary.open ?? alerts.length} hint={`${summary.total ?? alerts.length} itens monitorados.`} icon={Bell} tone="amber" compact />
        <StatCard label="Criticos" value={summary.critical ?? 0} hint="Itens que exigem revisao prioritaria." icon={ShieldAlert} tone="rose" compact />
        <StatCard label="Eventos Alpha" value={summary.alphaEvents ?? 0} hint="Mesma fonte do Resumo Inteligente." icon={Sparkles} tone="sky" compact />
        <StatCard label="Guardian" value={summary.guardian ?? 0} hint="Saude, score e criterios internos." icon={Activity} tone="emerald" compact />
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <h3 className="font-semibold text-stone-950">Fila de acompanhamento</h3>
          <p className="mt-1 text-xs text-stone-500">
            Quando o Alpha detectar algo relevante, ele aparece aqui. Itens do Alpha sao recalculados ao abrir ou atualizar a pagina.
          </p>
        </div>

        {alerts.length ? (
          <div className="divide-y divide-stone-200">
            {alerts.map((alert) => (
              <article key={alert.id} className="p-4 hover:bg-stone-50">
                <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                  <div className="flex min-w-0 gap-3">
                    <span className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${severity[alert.severity] || severity.info}`}>
                      <Bell size={17} />
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-md border px-2 py-1 text-[0.66rem] font-semibold uppercase tracking-[0.1em] ${severity[alert.severity] || severity.info}`}>
                          {severityLabel[alert.severity] || alert.severity}
                        </span>
                        {alert.ticker ? <span className="brand-badge rounded-md px-2 py-1 text-[0.66rem] font-semibold">{alert.ticker}</span> : null}
                        {alert.priority ? (
                          <span className="rounded-md border border-stone-200 bg-stone-50 px-2 py-1 text-[0.66rem] font-semibold uppercase tracking-[0.1em] text-stone-500">
                            Prioridade {alert.priority}
                          </span>
                        ) : null}
                        <span className="rounded-md border border-stone-200 bg-stone-50 px-2 py-1 text-[0.66rem] font-semibold uppercase tracking-[0.1em] text-stone-500">
                          {sourceLabel(alert.source)}
                        </span>
                        <span className="rounded-md border border-stone-200 bg-stone-50 px-2 py-1 text-[0.66rem] font-semibold uppercase tracking-[0.1em] text-stone-500">
                          {statusLabel(alert.status)}
                        </span>
                      </div>
                      <h3 className="mt-2 font-semibold text-stone-950">{alert.title}</h3>
                      <p className="mt-1 text-sm leading-6 text-stone-600">{alert.message}</p>
                      {alert.impact ? <p className="mt-2 text-xs leading-5 text-stone-500">{alert.impact}</p> : null}
                      {alert.recommendedAction ? (
                        <p className="mt-2 rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold leading-5 text-amber-200">
                          {alert.recommendedAction}
                        </p>
                      ) : null}
                      {alert.confidence ? (
                        <p className="mt-2 text-[0.68rem] uppercase tracking-[0.12em] text-stone-500">
                          Confianca: {alert.confidence}
                        </p>
                      ) : null}
                      <p className="mt-2 text-xs text-stone-500">{formatDate(alert.triggeredAt)}</p>
                    </div>
                  </div>

                  {alert.readOnly ? (
                    <span className="inline-flex h-9 shrink-0 items-center justify-center rounded-lg border border-stone-200 bg-stone-50 px-3 text-xs font-semibold uppercase tracking-[0.1em] text-stone-500">
                      {sourceLabel(alert.source)}
                    </span>
                  ) : (
                    <button onClick={() => markRead(alert)} className="btn-secondary h-9 shrink-0 px-3 text-sm" disabled={alert.isRead}>
                      <CheckCircle2 size={16} />
                      {alert.isRead ? "Lido" : "Marcar lido"}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="p-6">
            <div className="rounded-lg border border-stone-200 bg-stone-50 p-5">
              <p className="font-semibold text-stone-950">Nenhum alerta ativo agora.</p>
              <p className="mt-1 text-sm leading-6 text-stone-500">
                O Alpha vai preencher esta area quando detectar concentracao, score fraco, risco, evento de renda ou desequilibrio relevante.
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
