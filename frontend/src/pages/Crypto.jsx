import { Bitcoin, RefreshCw, Save, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import StatCard from "../components/StatCard.jsx";
import { apiFetch } from "../lib/api.js";
import { currency, money, pct, scoreColor } from "../lib/format.js";

const today = new Date().toISOString().slice(0, 10);

const initialForm = {
  symbol: "BTC",
  name: "Bitcoin",
  category: "reserva de valor",
  currency: "BRL",
  type: "buy",
  date: today,
  quantity: "0.001",
  price: "350000",
  fees: "0",
  exchange: "Binance",
  wallet: "",
};

const categories = [
  "reserva de valor",
  "smart contract",
  "stablecoin",
  "DeFi",
  "meme coin",
  "infraestrutura",
  "exchange token",
  "outro",
];

export default function Crypto({ token }) {
  const [data, setData] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [removingAssetId, setRemovingAssetId] = useState("");

  const load = () => apiFetch("/crypto", { token }).then(setData).catch((err) => setError(err.message));

  useEffect(() => {
    load();
  }, [token]);

  const metrics = useMemo(() => data?.metrics || {}, [data]);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setStatus("");
    setError("");
    try {
      await apiFetch("/crypto/transactions", {
        method: "POST",
        token,
        body: {
          ...form,
          quantity: Number(form.quantity),
          price: Number(form.price),
          fees: Number(form.fees || 0),
        },
      });
      setStatus("Operacao de cripto registrada.");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function syncMarket() {
    setSyncing(true);
    setStatus("");
    setError("");
    try {
      const result = await apiFetch("/crypto/sync-market", { method: "POST", token });
      setStatus(`Atualizacao cripto: ${result.updated?.length || 0} atualizada(s), ${result.skipped?.length || 0} sem novos dados.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  }

  async function removePosition(position) {
    const confirmed = window.confirm(`Remover ${position.ticker} da carteira cripto? Isso limpa suas movimentacoes desse ativo.`);
    if (!confirmed) return;
    setRemovingAssetId(position.assetId);
    setStatus("");
    setError("");
    try {
      const result = await apiFetch(`/portfolio/positions/${position.assetId}`, { method: "DELETE", token });
      setStatus(result.message || "Cripto removida da carteira.");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setRemovingAssetId("");
    }
  }

  if (!data && !error) return <LoadingState />;

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Cripto 360</p>
          <h2 className="text-2xl font-semibold text-stone-950">Carteira cripto</h2>
        </div>
        <div className="flex max-w-2xl flex-col items-start gap-3 sm:items-end">
          <p className="text-sm leading-6 text-stone-500 sm:text-right">
            Cripto entra no patrimonio total, mas nao entra no radar de dividendos. O score considera categoria, concentracao e risco.
          </p>
          <button onClick={syncMarket} className="btn-secondary h-10 px-3 text-sm" disabled={syncing}>
            <RefreshCw size={16} />
            {syncing ? "Atualizando" : "Atualizar CoinMarketCap"}
          </button>
        </div>
      </header>

      {error ? <ErrorState message={error} /> : null}
      {status ? <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">{status}</p> : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <StatCard label="Patrimonio cripto" value={currency.format(metrics.cryptoEquity || 0)} hint="Valor atual das criptos." icon={Bitcoin} tone="amber" />
        <StatCard label="Investido cripto" value={currency.format(metrics.cryptoInvested || 0)} hint="Capital aportado em cripto." icon={Bitcoin} tone="sky" />
        <StatCard label="Lucro/prejuizo" value={currency.format(metrics.cryptoPnl || 0)} hint={pct(metrics.cryptoPnlPct || 0)} icon={Bitcoin} tone={(metrics.cryptoPnl || 0) >= 0 ? "emerald" : "rose"} />
        <StatCard label="Peso no total" value={pct(metrics.cryptoWeightTotal || 0)} hint="Peso da cripto na carteira 360." icon={Bitcoin} tone="amber" />
        <StatCard label="Maior cripto" value={metrics.largestCrypto || "-"} hint="Maior posicao cripto atual." icon={Bitcoin} tone="sky" />
        <StatCard label="Risco cripto" value={metrics.cryptoRisk || "controlado"} hint="Leitura por peso e concentracao." icon={Bitcoin} tone={metrics.cryptoRisk === "alto" ? "rose" : "emerald"} />
      </section>

      <section className="surface p-4">
        <div className="mb-4 flex items-center gap-2">
          <Bitcoin size={18} className="text-amber-700" />
          <h3 className="font-semibold text-stone-950">Registrar compra ou venda de cripto</h3>
        </div>
        <form onSubmit={submit} className="grid gap-3 md:grid-cols-4 xl:grid-cols-12">
          <input className="field xl:col-span-2" value={form.symbol} onChange={(event) => setForm({ ...form, symbol: event.target.value.toUpperCase() })} placeholder="Simbolo" />
          <input className="field xl:col-span-2" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Nome" />
          <select className="field xl:col-span-2" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
            {categories.map((category) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
          <select className="field xl:col-span-2" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}>
            <option value="buy">Compra</option>
            <option value="sell">Venda</option>
          </select>
          <select className="field xl:col-span-2" value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value })}>
            <option value="BRL">BRL</option>
            <option value="USD">USD</option>
          </select>
          <input className="field xl:col-span-2" type="date" value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} />
          <input className="field xl:col-span-2" type="number" step="0.00000001" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} placeholder="Quantidade" />
          <input className="field xl:col-span-2" type="number" step="0.01" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} placeholder="Preco unitario" />
          <input className="field xl:col-span-2" type="number" step="0.01" value={form.fees} onChange={(event) => setForm({ ...form, fees: event.target.value })} placeholder="Taxa" />
          <input className="field xl:col-span-2" value={form.exchange} onChange={(event) => setForm({ ...form, exchange: event.target.value })} placeholder="Exchange/corretora" />
          <input className="field xl:col-span-2" value={form.wallet} onChange={(event) => setForm({ ...form, wallet: event.target.value })} placeholder="Wallet opcional" />
          <button className="btn-primary h-12 px-4 text-sm xl:col-span-2" disabled={loading}>
            <Save size={16} />
            {loading ? "Salvando" : "Salvar cripto"}
          </button>
        </form>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <h3 className="font-semibold text-stone-950">Criptos em carteira</h3>
          <p className="text-xs text-stone-500">Cotacao pode vir do CoinMarketCap quando a chave estiver configurada.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1280px] text-left text-sm">
            <thead className="bg-stone-50 text-xs uppercase text-stone-500">
              <tr>
                {["Cripto", "Categoria", "Qtd.", "Preco medio", "Preco atual", "Investido", "Atual", "P/L", "Rent.", "Peso cripto", "Peso total", "Exchange", "Wallet", "Score", "Remover"].map((head) => (
                  <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {data?.positions.map((position) => (
                <tr key={position.assetId} className="hover:bg-stone-50">
                  <td className="px-4 py-3">
                    <p className="font-semibold text-stone-950">{position.ticker}</p>
                    <p className="text-xs text-stone-500">{position.name}</p>
                  </td>
                  <td className="px-4 py-3">{position.category}</td>
                  <td className="px-4 py-3">{position.quantity}</td>
                  <td className="px-4 py-3">{money(position.averagePrice, position.currency)}</td>
                  <td className="px-4 py-3">{money(position.currentPrice, position.currency)}</td>
                  <td className="px-4 py-3">{money(position.investedValue, position.currency)}</td>
                  <td className="px-4 py-3">{money(position.currentValue, position.currency)}</td>
                  <td className={`px-4 py-3 font-semibold ${position.pnl >= 0 ? "text-emerald-700" : "text-rose-700"}`}>{money(position.pnl, position.currency)}</td>
                  <td className="px-4 py-3">{pct(position.returnPct)}</td>
                  <td className="px-4 py-3">{pct(position.cryptoWeight)}</td>
                  <td className="px-4 py-3">{pct(position.totalWeight)}</td>
                  <td className="px-4 py-3">{position.exchange || "-"}</td>
                  <td className="px-4 py-3">{position.wallet || "-"}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${scoreColor(position.cryptoScore)}`}>
                      {position.cryptoScore} - {position.cryptoClassification}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      className="icon-button"
                      onClick={() => removePosition(position)}
                      disabled={removingAssetId === position.assetId}
                      title={`Remover ${position.ticker}`}
                      type="button"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {!data?.positions.length ? (
                <tr>
                  <td colSpan={15} className="px-4 py-6 text-sm text-stone-500">
                    Nenhuma cripto cadastrada ainda.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
