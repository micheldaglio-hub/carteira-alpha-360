import { Gauge, RefreshCw, ShieldAlert, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import { apiFetch } from "../lib/api.js";
import { currency, pct, scoreColor } from "../lib/format.js";

const copy = {
  dividends: {
    eyebrow: "Radar de proventos",
    title: "Sua carteira por renda passiva",
    endpoint: "/radar/dividends",
    score: "scoreDividendos",
    text: "Mostra apenas os ativos que estao na sua carteira. Analisa dividendos, JCP, rendimentos recorrentes, historico, frequencia, consistencia, payout e risco de corte.",
  },
  growth: {
    eyebrow: "Radar de crescimento",
    title: "Sua carteira por crescimento",
    endpoint: "/radar/growth",
    score: "scoreCrescimento",
    text: "Mostra apenas os ativos que estao na sua carteira. Dados parciais aparecem sinalizados quando a fonte externa ainda nao trouxe fundamentos completos.",
  },
  radar: {
    eyebrow: "Radar de ativos",
    title: "Leitura Alpha da sua carteira",
    endpoint: "/radar/assets",
    score: "scoreFinal",
    text: "Nao e lista de compra. E uma leitura dos ativos que voce possui, combinando proventos, crescimento, seguranca, valuation e risco.",
  },
};

export default function Radar({ token, kind = "radar" }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [removingAssetId, setRemovingAssetId] = useState("");
  const [syncing, setSyncing] = useState(false);
  const config = copy[kind];

  const load = () => {
    setError("");
    return apiFetch(config.endpoint, { token }).then(setData).catch((err) => setError(err.message));
  };

  useEffect(() => {
    setData(null);
    setStatus("");
    load();
  }, [token, config.endpoint]);

  async function removeAsset(asset) {
    const confirmed = window.confirm(
      `Remover ${asset.ticker} da sua carteira? Isso limpa movimentacoes, proventos, alertas e metas desse ativo apenas para o seu usuario.`
    );
    if (!confirmed) return;
    setRemovingAssetId(asset.assetId);
    setStatus("");
    setError("");
    try {
      const result = await apiFetch(`/portfolio/positions/${asset.assetId}`, { method: "DELETE", token });
      setStatus(result.message || "Ativo removido da carteira.");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setRemovingAssetId("");
    }
  }

  async function syncMarket() {
    setSyncing(true);
    setStatus("");
    setError("");
    try {
      const result = await apiFetch("/portfolio/sync-market", { method: "POST", token });
      const updated = result.updated?.length || 0;
      const skipped = result.skipped?.length || 0;
      setStatus(`Atualizacao concluida: ${updated} ativo(s) atualizado(s), ${skipped} sem novos dados.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  }

  const leaders = useMemo(() => data?.assets?.slice(0, 3) || [], [data]);

  if (error && !data) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">{config.eyebrow}</p>
          <h2 className="text-2xl font-semibold text-stone-950">{config.title}</h2>
        </div>
        <div className="flex max-w-2xl flex-col items-start gap-3 sm:items-end">
          <p className="text-sm leading-6 text-stone-500 sm:text-right">{config.text}</p>
          <button onClick={syncMarket} className="btn-secondary h-10 px-3 text-sm" disabled={syncing}>
            <RefreshCw size={16} />
            {syncing ? "Atualizando" : "Atualizar dados"}
          </button>
        </div>
      </header>

      {error ? <ErrorState message={error} /> : null}
      {status ? <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">{status}</p> : null}

      {leaders.length ? (
        <section className="grid gap-4 lg:grid-cols-3">
          {leaders.map((asset, index) => (
            <div key={asset.ticker} className="surface p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase text-stone-500">#{index + 1}</p>
                  <h3 className="mt-2 text-xl font-semibold text-stone-950">{asset.ticker}</h3>
                  <p className="text-sm text-stone-500">{asset.name}</p>
                </div>
                <span className={`rounded-lg border px-3 py-2 text-sm font-semibold ${scoreColor(asset[config.score])}`}>
                  {asset[config.score]}/100
                </span>
              </div>
              <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold">
                <span className="rounded-lg bg-stone-100 px-2.5 py-1.5 text-stone-700">{asset.term}</span>
                <span className="rounded-lg bg-emerald-50 px-2.5 py-1.5 text-emerald-700">{asset.classification}</span>
                {asset.dataStatus === "parcial" ? (
                  <span className="rounded-lg bg-amber-50 px-2.5 py-1.5 text-amber-700">Dados parciais</span>
                ) : null}
              </div>
            </div>
          ))}
        </section>
      ) : null}

      <section className="surface overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-stone-200 px-4 py-3">
          <div className="flex items-center gap-2">
            <Gauge size={18} className="text-amber-700" />
            <h3 className="font-semibold text-stone-950">Ranking da sua carteira</h3>
          </div>
          <p className="text-xs font-medium text-stone-500">{data.assets.length} ativo(s)</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1220px] text-left text-sm">
            <thead className="bg-stone-50 text-xs uppercase text-stone-500">
              <tr>
                {["Ativo", "Preco", "Yield", "Proventos", "Crescimento", "Seguranca", "Valuation", "Risco", "Final", "Classificacao", "Dados", "Leitura", "Remover"].map((head) => (
                  <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {data.assets.map((asset) => (
                <tr key={asset.assetId} className="align-top hover:bg-stone-50">
                  <td className="px-4 py-3">
                    <p className="font-semibold text-stone-950">{asset.ticker}</p>
                    <p className="text-xs text-stone-500">{asset.sector}</p>
                  </td>
                  <td className="px-4 py-3">{currency.format(asset.price)}</td>
                  <td className="px-4 py-3">{pct(asset.dividendYield)}</td>
                  <td className="px-4 py-3">{asset.scoreDividendos}</td>
                  <td className="px-4 py-3">{asset.scoreCrescimento}</td>
                  <td className="px-4 py-3">{asset.scoreSeguranca}</td>
                  <td className="px-4 py-3">{asset.scoreValuation}</td>
                  <td className="px-4 py-3">{asset.scoreRisco}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${scoreColor(asset.scoreFinal)}`}>{asset.scoreFinal}</span>
                  </td>
                  <td className="px-4 py-3">{asset.classification}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${asset.dataStatus === "parcial" ? "border-amber-200 bg-amber-50 text-amber-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
                      {asset.dataStatus === "parcial" ? "Parciais" : "Completos"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <p className="max-w-md text-xs leading-5 text-stone-600">{kind === "growth" ? asset.growthJustification : kind === "dividends" ? asset.dividendJustification : asset.finalJustification}</p>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      className="icon-button"
                      onClick={() => removeAsset(asset)}
                      disabled={removingAssetId === asset.assetId}
                      title={`Remover ${asset.ticker} da carteira`}
                      type="button"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {!data.assets.length ? (
                <tr>
                  <td className="px-4 py-6 text-sm text-stone-500" colSpan={13}>
                    Nenhum ativo em carteira para analisar nesta aba.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="surface p-4">
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-amber-600" />
            <h3 className="font-semibold text-stone-950">Como ler o score</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-stone-600">
            A pontuacao vai de 0 a 100 e serve como filtro analitico da sua carteira. Ela nao e ordem operacional e nao substitui sua politica de investimento.
          </p>
        </div>
        <div className="surface p-4">
          <div className="flex items-center gap-2">
            <ShieldAlert size={18} className="text-rose-700" />
            <h3 className="font-semibold text-stone-950">Dados parciais</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-stone-600">
            Quando uma empresa aparece com dados parciais, a fonte externa ainda nao entregou fundamentos suficientes. O sistema evita tratar zeros como analise definitiva.
          </p>
        </div>
      </section>
    </div>
  );
}
