import { DatabaseZap, KeyRound, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import { apiFetch } from "../lib/api.js";

export default function Settings({ token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/settings", { token }).then(setData).catch((err) => setError(err.message));
  }, [token]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <div className="space-y-5">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Configurações</p>
        <h2 className="text-2xl font-semibold text-stone-950">Arquitetura e integrações</h2>
      </header>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="surface p-4">
          <DatabaseZap className="text-amber-700" size={22} />
          <h3 className="mt-3 font-semibold text-stone-950">Provider ativo</h3>
          <p className="mt-2 text-sm text-stone-600">{data.marketDataProvider}</p>
        </div>
        <div className="surface p-4">
          <ShieldCheck className="text-emerald-700" size={22} />
          <h3 className="mt-3 font-semibold text-stone-950">Ambiente</h3>
          <p className="mt-2 text-sm text-stone-600">{data.environment}</p>
        </div>
        <div className="surface p-4">
          <KeyRound className="text-amber-700" size={22} />
          <h3 className="mt-3 font-semibold text-stone-950">Sessão</h3>
          <p className="mt-2 text-sm text-stone-600">API protegida por token assinado.</p>
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <h3 className="font-semibold text-stone-950">Fontes externas preparadas</h3>
          <p className="text-xs text-stone-500">Camada de providers para trocar ou adicionar APIs no futuro.</p>
        </div>
        <div className="divide-y divide-stone-100">
          {data.externalSources.map((source, index) => (
            <div key={`${source.name}-${index}`} className="grid gap-2 px-4 py-3 md:grid-cols-[0.7fr_0.4fr_1.3fr]">
              <p className="font-semibold text-stone-950">{source.name}</p>
              <p className="text-sm font-semibold text-amber-700">{source.status}</p>
              <p className="text-sm text-stone-500">{source.notes || source.baseUrl || (source.requiresToken ? "Requer token de API." : "")}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="surface p-4">
        <h3 className="font-semibold text-stone-950">Princípios do produto</h3>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {data.principles.map((principle) => (
            <div key={principle} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-700">
              {principle}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
