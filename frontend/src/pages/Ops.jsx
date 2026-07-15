import { Activity, DatabaseBackup, Play, RefreshCw, ScrollText, ServerCog } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import StatCard from "../components/StatCard.jsx";
import { apiFetch } from "../lib/api.js";

function statusTone(status) {
  if (status === "success" || status === "operational") return "text-emerald-300";
  if (status === "error" || status === "critical") return "text-rose-300";
  return "text-amber-200";
}

export default function Ops({ token }) {
  const [data, setData] = useState(null);
  const [audit, setAudit] = useState(null);
  const [jobs, setJobs] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [observability, auditPayload, jobsPayload] = await Promise.all([
        apiFetch("/ops/observability", { token }),
        apiFetch("/ops/audit?limit=60", { token }),
        apiFetch("/ops/jobs?limit=30", { token }),
      ]);
      setData(observability);
      setAudit(auditPayload);
      setJobs(jobsPayload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function runJob(jobName) {
    setError("");
    setLoading(true);
    try {
      await apiFetch(`/ops/jobs/${encodeURIComponent(jobName)}/run`, { method: "POST", token });
      await load();
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

  if (error && !data) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Carregando saude do sistema..." />;

  const obs = data.observability || {};
  const jobStatus = jobs?.status || data.jobs || {};
  const auditSummary = audit?.summary || data.audit || {};
  const latestRuns = jobStatus.latestRuns || {};

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Sistema</p>
          <h2 className="text-2xl font-semibold text-stone-950">Saude do sistema</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
            Esta pagina mostra se o Carteira Alpha esta respondendo bem, quais rotinas foram executadas e quais acoes ficaram registradas para auditoria.
            Ela e mais tecnica e serve principalmente para suporte, producao e diagnostico.
          </p>
        </div>
        <button type="button" className="btn-primary h-10 px-4 text-sm" onClick={load} disabled={loading}>
          <RefreshCw size={16} />
          {loading ? "Atualizando" : "Atualizar"}
        </button>
      </header>

      {error ? <ErrorState message={error} /> : null}

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Acessos recentes" value={obs.requestsWindow || 0} hint={`Tempo medio ${obs.avgDurationMs || 0} ms`} icon={Activity} tone="amber" compact />
        <StatCard label="Sistema online" value={`${Math.round(obs.uptimeSeconds || 0)}s`} hint="Tempo desde que o backend abriu." icon={ServerCog} tone="emerald" compact />
        <StatCard label="Registros" value={auditSummary.total || 0} hint={`${auditSummary.warnings || 0} pontos de atencao`} icon={ScrollText} tone="sky" compact />
        <StatCard label="Rotinas" value={(jobStatus.registeredJobs || []).length} hint={jobStatus.jobsEnabled ? "Automaticas ligadas" : "Manual por enquanto"} icon={Play} tone={jobStatus.jobsEnabled ? "emerald" : "stone"} compact />
        <StatCard label="Backup" value="Pronto" hint="SQLite e PostgreSQL/Supabase." icon={DatabaseBackup} tone="amber" compact />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div className="surface overflow-hidden">
          <div className="border-b border-stone-200 p-4">
            <h3 className="font-semibold text-stone-950">Rotinas automaticas</h3>
            <p className="mt-1 text-xs text-stone-500">Tarefas internas como limpeza, checagem de saude e snapshots. Normalmente voce nao precisa mexer aqui.</p>
          </div>
          <div className="divide-y divide-stone-200">
            {(jobStatus.registeredJobs || []).map((jobName) => {
              const run = latestRuns[jobName];
              return (
                <div key={jobName} className="flex items-center justify-between gap-3 p-4">
                  <div>
                    <p className="text-sm font-semibold text-stone-950">{jobName}</p>
                    <p className={`mt-1 text-xs ${statusTone(run?.status)}`}>{run?.status || "sem execucao"}</p>
                    <p className="mt-1 text-xs text-stone-500">{run?.message || "Aguardando primeira execucao."}</p>
                  </div>
                  <button type="button" className="btn-secondary h-9 px-3 text-xs" onClick={() => runJob(jobName)} disabled={loading}>
                    <Play size={14} />
                    Rodar
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        <div className="surface overflow-hidden">
          <div className="border-b border-stone-200 p-4">
            <h3 className="font-semibold text-stone-950">Acessos recentes</h3>
            <p className="mt-1 text-xs text-stone-500">Mostra as ultimas chamadas do sistema para diagnosticar lentidao ou erro.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="premium-table min-w-full text-left text-sm">
              <thead>
                <tr>
                  <th>Rota</th>
                  <th>Status</th>
                  <th>Tempo</th>
                  <th>Codigo tecnico</th>
                </tr>
              </thead>
              <tbody>
                {(obs.recentRequests || []).slice().reverse().map((request) => (
                  <tr key={request.request_id}>
                    <td>{request.method} {request.path}</td>
                    <td className={Number(request.status_code) >= 400 ? "text-rose-300" : "text-emerald-300"}>{request.status_code}</td>
                    <td>{request.duration_ms} ms</td>
                    <td className="max-w-40 truncate text-xs text-stone-500">{request.request_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 p-4">
          <h3 className="font-semibold text-stone-950">Historico de auditoria</h3>
          <p className="mt-1 text-xs text-stone-500">Registro de logins, alteracoes, rotinas e acoes importantes feitas no sistema.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="premium-table min-w-full text-left text-sm">
            <thead>
              <tr>
                <th>Data</th>
                <th>Evento</th>
                <th>Acao</th>
                <th>Severidade</th>
                <th>Mensagem</th>
              </tr>
            </thead>
            <tbody>
              {(audit?.events || []).map((event) => (
                <tr key={event.id}>
                  <td className="whitespace-nowrap text-xs text-stone-500">{new Date(event.createdAt).toLocaleString("pt-BR")}</td>
                  <td>{event.eventType}</td>
                  <td>{event.action}</td>
                  <td className={statusTone(event.severity)}>{event.severity}</td>
                  <td className="max-w-xl text-xs leading-5 text-stone-500">{event.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
