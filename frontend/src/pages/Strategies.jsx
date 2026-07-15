import { Brain, Compass, Gauge, Globe2, ShieldCheck, Sparkles, Target, WalletCards } from "lucide-react";
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
import { pct } from "../lib/format.js";

const axisTick = { fontSize: 11, fill: "var(--muted)" };
const tooltipStyle = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)" };
const palette = ["#f5c84b", "#3bd19f", "#74c7ff", "#a78bfa", "#f97373", "#f59e0b", "#94a3b8"];

function scoreTone(score) {
  if (score >= 78) return "border-emerald-400/35 bg-emerald-500/10 text-emerald-200";
  if (score >= 64) return "border-amber-400/35 bg-amber-500/10 text-amber-200";
  if (score >= 48) return "border-sky-400/35 bg-sky-500/10 text-sky-200";
  return "border-rose-400/35 bg-rose-500/10 text-rose-200";
}

function StrategyBadge({ score, label }) {
  return (
    <span className={`rounded-lg border px-2.5 py-1 text-[0.72rem] font-semibold uppercase tracking-[0.08em] ${scoreTone(score)}`}>
      {label}
    </span>
  );
}

export default function Strategies({ token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState("");

  useEffect(() => {
    let active = true;
    setError("");
    apiFetch("/wealth-os/strategies", { token })
      .then((payload) => {
        if (!active) return;
        setData(payload);
        setSelectedId(payload.primaryStrategy || payload.assessments?.[0]?.strategy?.id || "");
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [token]);

  const selected = useMemo(
    () => data?.assessments?.find((item) => item.strategy.id === selectedId) || data?.assessments?.[0],
    [data, selectedId]
  );

  const allocationRows = useMemo(() => {
    const target = selected?.strategy?.targetAllocation || {};
    const current = data?.currentAllocation || {};
    return Object.keys({ ...target, ...current }).map((key) => ({
      name: key,
      atual: Number(current[key] || 0),
      alvo: Number(target[key] || 0),
    }));
  }, [data, selected]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Carregando Strategy Engine 2.0..." />;

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Strategy Engine 2.0</p>
          <h2 className="text-2xl font-semibold text-stone-950">Perfis patrimoniais</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
            O Alpha compara sua carteira com estrategias de dividendos, crescimento, global, cripto controlado,
            aposentadoria e filosofias consagradas. A leitura orienta estudo e rebalanceamento, sem ordem automatica.
          </p>
        </div>
        <div className="surface max-w-xl p-3 text-xs leading-5 text-stone-500">
          <p className="font-semibold uppercase tracking-[0.14em] text-brand">Leitura principal</p>
          <p className="mt-1 text-sm font-semibold text-stone-950">{data.headline}</p>
          <p className="mt-2">Atualizado em {new Date(data.updatedAt).toLocaleString("pt-BR")}.</p>
        </div>
      </header>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Perfil dominante" value={selected?.strategy?.name || "-"} hint={selected?.strategy?.archetype || "Aguardando leitura."} icon={Compass} tone="amber" compact />
        <StatCard label="Aderencia" value={`${Number(data.primaryScore || 0).toFixed(0)}/100`} hint={selected?.classification || "Sem classificacao."} icon={Gauge} tone="emerald" compact token={token} evidenceDomain="strategy" evidenceField="primaryScore" />
        <StatCard label="Exposicao global" value={pct(data.metrics?.globalExposure)} hint="ETFs globais e ativos fora de BRL." icon={Globe2} tone="sky" compact token={token} evidenceDomain="strategy" evidenceField="globalExposure" />
        <StatCard label="Cripto" value={pct(data.metrics?.cryptoWeight)} hint="Peso estimado na carteira atual." icon={Sparkles} tone={(data.metrics?.cryptoWeight || 0) > 12 ? "rose" : "amber"} compact token={token} evidenceDomain="strategy" evidenceField="cryptoWeight" />
        <StatCard label="Maior ativo" value={pct(data.metrics?.largestAssetWeight)} hint="Controle de concentracao." icon={ShieldCheck} tone="stone" compact token={token} evidenceDomain="strategy" evidenceField="largestAssetWeight" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div className="surface overflow-hidden">
          <div className="border-b border-stone-200 p-4">
            <div className="flex items-center gap-2">
              <Brain size={18} className="text-amber-500" />
              <h3 className="font-semibold text-stone-950">Ranking de estrategias</h3>
            </div>
            <p className="mt-1 text-xs text-stone-500">Compatibilidade calculada com alocacao, renda, concentracao, global, cripto e qualidade setorial.</p>
          </div>
          <div className="grid gap-2 p-3">
            {(data.assessments || []).map((item) => {
              const active = selected?.strategy?.id === item.strategy.id;
              return (
                <button
                  key={item.strategy.id}
                  type="button"
                  onClick={() => setSelectedId(item.strategy.id)}
                  className={`rounded-lg border p-3 text-left transition ${
                    active ? "border-amber-400/50 bg-amber-500/10" : "border-stone-200 bg-black/10 hover:border-amber-500/35"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-stone-950">{item.strategy.name}</p>
                      <p className="mt-1 text-xs text-stone-500">{item.strategy.archetype}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-stone-950">{Number(item.score || 0).toFixed(0)}</p>
                      <StrategyBadge score={item.score} label={item.classification} />
                    </div>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-stone-500">{item.headline}</p>
                </button>
              );
            })}
          </div>
        </div>

        <div className="surface p-4">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">{selected?.strategy?.archetype}</p>
              <h3 className="mt-1 text-xl font-semibold text-stone-950">{selected?.strategy?.name}</h3>
              <p className="mt-2 text-sm leading-6 text-stone-500">{selected?.strategy?.description}</p>
            </div>
            <StrategyBadge score={selected?.score || 0} label={`${Number(selected?.score || 0).toFixed(0)}/100`} />
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-stone-200 bg-stone-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">Risco</p>
              <p className="mt-1 text-sm font-semibold text-stone-950">{selected?.strategy?.riskProfile?.replaceAll("_", " ")}</p>
            </div>
            <div className="rounded-lg border border-stone-200 bg-stone-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">Horizonte</p>
              <p className="mt-1 text-sm font-semibold text-stone-950">{selected?.strategy?.timeHorizon}</p>
            </div>
            <div className="rounded-lg border border-stone-200 bg-stone-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">Ativos</p>
              <p className="mt-1 text-sm font-semibold text-stone-950">{Number(data.metrics?.assetCount || 0).toFixed(0)} monitorados</p>
            </div>
          </div>

          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={allocationRows} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" tick={axisTick} />
                <YAxis tickFormatter={(value) => `${value}%`} tick={axisTick} width={42} />
                <Tooltip formatter={(value) => pct(value)} contentStyle={tooltipStyle} />
                <Bar dataKey="atual" name="Atual" radius={[5, 5, 0, 0]} fill="#74c7ff" />
                <Bar dataKey="alvo" name="Alvo" radius={[5, 5, 0, 0]}>
                  {allocationRows.map((row, index) => (
                    <Cell key={row.name} fill={palette[index % palette.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="surface p-4">
          <div className="flex items-center gap-2">
            <Target size={18} className="text-amber-500" />
            <h3 className="font-semibold text-stone-950">Fatores do perfil selecionado</h3>
          </div>
          <div className="mt-3 grid gap-2">
            {(selected?.factors || []).map((factor) => (
              <div key={factor.id} className="rounded-lg border border-stone-200 bg-black/10 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-stone-950">{factor.label}</p>
                  <span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${scoreTone(factor.score)}`}>{Number(factor.score || 0).toFixed(0)}</span>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-stone-800">
                  <div className="h-1.5 rounded-full bg-brand" style={{ width: `${Math.max(2, Math.min(100, factor.score || 0))}%` }} />
                </div>
                <p className="mt-2 text-xs leading-5 text-stone-500">{factor.reading}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="surface p-4">
            <div className="flex items-center gap-2">
              <WalletCards size={18} className="text-emerald-500" />
              <h3 className="font-semibold text-stone-950">Leitura humana</h3>
            </div>
            <div className="mt-3 grid gap-2">
              {(selected?.strategy?.philosophy || []).map((item) => (
                <p key={item} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">{item}</p>
              ))}
            </div>
          </div>

          <div className="surface p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Proximos estudos</p>
            <div className="mt-3 grid gap-2">
              {(selected?.nextStudies || []).map((item) => (
                <p key={item} className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-200">{item}</p>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 p-4">
          <h3 className="font-semibold text-stone-950">Ativos que mais combinam com o perfil</h3>
          <p className="mt-1 text-xs text-stone-500">Pontuacao de encaixe estrategico dentro do perfil selecionado.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="premium-table min-w-full text-left text-sm">
            <thead>
              <tr>
                <th>Ativo</th>
                <th>Classe</th>
                <th>Setor</th>
                <th>Encaixe</th>
                <th>Leitura</th>
              </tr>
            </thead>
            <tbody>
              {(selected?.assetFits || []).map((asset) => (
                <tr key={`${selected.strategy.id}-${asset.ticker}`}>
                  <td>
                    <p className="font-semibold">{asset.ticker}</p>
                    <p className="text-xs text-stone-500">{asset.name}</p>
                  </td>
                  <td>{asset.assetClass}</td>
                  <td>{asset.sector}</td>
                  <td>
                    <span className={`rounded-lg border px-2 py-1 text-xs font-semibold ${scoreTone(asset.score)}`}>{Number(asset.score || 0).toFixed(0)} - {asset.fit}</span>
                  </td>
                  <td className="max-w-xl text-xs leading-5 text-stone-500">{asset.reading}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="surface p-4">
        <div className="flex items-center gap-2">
          <ShieldCheck size={18} className="text-amber-500" />
          <h3 className="font-semibold text-stone-950">Regras do motor</h3>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {(data.rules || []).map((rule) => (
            <p key={rule} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">{rule}</p>
          ))}
        </div>
      </section>
    </div>
  );
}
