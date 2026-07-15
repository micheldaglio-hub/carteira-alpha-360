import {
  CheckCircle2,
  Clock3,
  CreditCard,
  Crown,
  Download,
  Eye,
  FileText,
  Inbox,
  Lock,
  MailCheck,
  MousePointerClick,
  RefreshCw,
  ShieldCheck,
  TicketCheck,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import StatCard from "../components/StatCard.jsx";
import { apiDownload, apiFetch } from "../lib/api.js";

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString("pt-BR");
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function roleLabel(role) {
  const labels = {
    admin: "Administrador",
    editor: "Editor",
    reviewer: "Revisor",
    premium_subscriber: "Assinante Premium",
    free_user: "Usuario Free",
  };
  return labels[role] || role;
}

function entitlementLabel(key) {
  const labels = {
    "premium.research.preview": "Preview premium",
    "premium.research.read": "Leitura premium",
    "premium.pdf.download": "Download PDF",
    "premium.pdf.bulk_download": "Downloads em lote",
    "premium.publications.archive": "Arquivo historico",
    "premium.research.admin": "Admin premium",
  };
  return labels[key] || key;
}

function statusText(value) {
  return String(value || "sem status").replaceAll("_", " ");
}

function formatMoney(value, currency = "BRL") {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency });
}

function deliveryStatusClass(status) {
  const value = String(status || "pending");
  if (value === "downloaded") return "border-emerald-400/30 bg-emerald-500/10 text-emerald-300";
  if (["opened", "clicked", "received"].includes(value)) return "border-sky-400/30 bg-sky-500/10 text-sky-300";
  if (["failed", "skipped"].includes(value)) return "border-rose-400/30 bg-rose-500/10 text-rose-300";
  return "border-amber-400/30 bg-amber-500/10 text-amber-300";
}

function DeliveryIcon({ status }) {
  const icons = {
    downloaded: Download,
    clicked: MousePointerClick,
    opened: Eye,
    received: MailCheck,
    sent: MailCheck,
    failed: TriangleAlert,
    skipped: TriangleAlert,
    pending: Clock3,
  };
  const Icon = icons[String(status || "pending")] || Clock3;
  return <Icon size={15} />;
}

export default function PremiumSubscriber({ token }) {
  const [data, setData] = useState(null);
  const [plans, setPlans] = useState([]);
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const activeEntitlements = data?.access?.activeEntitlements || [];
  const roleNames = data?.rbac?.roleNames || [];
  const activeSubscription = data?.activeSubscription || null;
  const deliveryInbox = data?.deliveryInbox?.items || [];
  const deliverySummary = data?.deliveryInbox?.summary || {};
  const pdfDownloadEntitlements = activeEntitlements.filter((item) =>
    ["premium.pdf.download", "premium.pdf.bulk_download", "premium.research.admin"].includes(item.entitlementKey)
  );
  const downloadUsage = useMemo(() => {
    const used = pdfDownloadEntitlements.reduce((sum, item) => sum + Number(item.usageCount || 0), 0);
    const limit = pdfDownloadEntitlements.reduce((sum, item) => sum + Number(item.usageLimit || 0), 0);
    return { used, limit };
  }, [pdfDownloadEntitlements]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [payload, planPayload, billingPayload] = await Promise.all([
        apiFetch("/premium/subscriber/home", { token }),
        apiFetch("/premium/plans", { token }),
        apiFetch("/billing/me", { token }),
      ]);
      setData(payload);
      setPlans(planPayload.items || []);
      setBilling(billingPayload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function downloadArtifact(artifact) {
    setBusyId(artifact.id);
    setError("");
    setNotice("");
    try {
      const result = await apiDownload(`/premium/artifacts/${artifact.id}/download`, {
        token,
        filename: `${artifact.title || "carteira-alpha-premium"}.pdf`,
      });
      setNotice(`PDF baixado: ${result.filename}`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId("");
    }
  }

  async function startCheckout(plan, billingCycle) {
    setBusyId(`${plan.code}:${billingCycle}`);
    setError("");
    setNotice("");
    try {
      const result = await apiFetch("/billing/checkout/sessions", {
        method: "POST",
        token,
        body: {
          plan_code: plan.code,
          billing_cycle: billingCycle,
          success_url: `${window.location.origin}${window.location.pathname}`,
          cancel_url: `${window.location.origin}${window.location.pathname}`,
        },
      });
      if (result.providerMode === "test" || result.checkout?.provider === "mock") {
        await apiFetch(`/billing/mock/checkout/${result.checkout.id}/success`, {
          method: "POST",
          token,
        });
        setNotice(`Pagamento de teste aprovado. Plano ${plan.name} ativado.`);
        await load();
        return;
      }
      if (result.checkout?.checkoutUrl) {
        window.location.href = result.checkout.checkoutUrl;
      } else {
        setNotice("Checkout criado, mas o provedor nao retornou URL de pagamento.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId("");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (loading && !data) return <LoadingState label="Carregando Area Premium..." />;

  return (
    <div className="space-y-4">
      <header className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Area Premium</p>
          <h2 className="text-2xl font-semibold text-stone-950">Central do assinante</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
            Consulte seu plano, permissoes, edicoes premium liberadas e historico de downloads.
          </p>
        </div>
        <button type="button" className="btn-secondary h-10 px-4 text-sm" onClick={load} disabled={loading}>
          <RefreshCw size={16} />
          Atualizar
        </button>
      </header>

      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="rounded-lg border border-emerald-400/25 bg-emerald-500/10 px-4 py-3 text-sm font-semibold text-emerald-200">{notice}</div> : null}

      <section className="grid gap-3 xl:grid-cols-5">
        <StatCard
          label="Plano atual"
          value={activeSubscription?.planCode || "Sem assinatura"}
          hint={activeSubscription?.currentPeriodEnd ? `Valido ate ${formatDate(activeSubscription.currentPeriodEnd)}` : "Acesso premium depende de plano ativo."}
          icon={Crown}
          tone={activeSubscription ? "amber" : "stone"}
          compact
        />
        <StatCard
          label="Papel de acesso"
          value={roleNames.map(roleLabel).join(", ") || "Sem papel"}
          hint="RBAC controla o que seu usuario pode ver ou operar."
          icon={ShieldCheck}
          tone={data?.rbac?.isEditorial ? "sky" : "emerald"}
          compact
        />
        <StatCard
          label="Downloads"
          value={downloadUsage.limit ? `${downloadUsage.used}/${downloadUsage.limit}` : String(downloadUsage.used)}
          hint="Uso de PDFs no periodo vigente."
          icon={Download}
          tone="emerald"
          compact
        />
        <StatCard
          label="Edicoes liberadas"
          value={data?.availableDownloadCount || 0}
          hint={`${data?.editionCount || 0} edicao(oes) aprovada(s) encontradas.`}
          icon={FileText}
          tone="amber"
          compact
        />
        <StatCard
          label="Entregas"
          value={`${Number(deliverySummary.downloaded || 0)}/${Number(deliverySummary.total || 0)}`}
          hint={`${Number(deliverySummary.pending || 0)} pendente(s), ${Number(deliverySummary.received || 0)} recebida(s).`}
          icon={Inbox}
          tone="sky"
          compact
        />
      </section>

      {!data?.canReadPremium ? (
        <div className="surface flex items-start gap-3 p-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-amber-400/35 bg-amber-500/10 text-amber-300">
            <Lock size={17} />
          </div>
          <div>
            <h3 className="font-semibold text-stone-950">Seu plano ainda nao libera edicoes premium completas</h3>
            <p className="mt-1 text-sm leading-6 text-stone-500">
              Quando uma assinatura premium estiver ativa, as edicoes aprovadas e os PDFs aparecerao aqui com download autenticado.
            </p>
          </div>
        </div>
      ) : null}

      <section className="surface overflow-hidden">
        <div className="flex flex-col gap-2 border-b border-stone-700 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="font-semibold text-stone-950">Notification Center</h3>
            <p className="mt-1 text-xs text-stone-500">
              Caixa de entregas das edicoes premium: recebidas, abertas, baixadas e pendentes.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-lg border border-stone-700 px-2 py-1 text-stone-400">Total {deliverySummary.total || 0}</span>
            <span className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-2 py-1 font-semibold text-amber-300">Pendentes {deliverySummary.pending || 0}</span>
            <span className="rounded-lg border border-sky-400/30 bg-sky-500/10 px-2 py-1 font-semibold text-sky-300">Recebidas {(deliverySummary.received || 0) + (deliverySummary.opened || 0) + (deliverySummary.clicked || 0)}</span>
            <span className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-2 py-1 font-semibold text-emerald-300">Baixadas {deliverySummary.downloaded || 0}</span>
          </div>
        </div>
        <div className="divide-y divide-stone-800">
          {deliveryInbox.length === 0 ? (
            <div className="p-4 text-sm text-stone-500">
              Nenhuma edicao foi entregue para este usuario ainda. Quando uma campanha premium for disparada, ela aparecera aqui.
            </div>
          ) : null}
          {deliveryInbox.slice(0, 8).map((item) => (
            <article key={item.id} className="p-4">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-[0.68rem] font-bold uppercase tracking-[0.1em] ${deliveryStatusClass(item.deliveryStatus)}`}>
                      <DeliveryIcon status={item.deliveryStatus} />
                      {item.deliveryStatusLabel}
                    </span>
                    <span className="rounded-lg border border-stone-700 px-2 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-stone-400">
                      {item.publication?.period || "sem periodo"}
                    </span>
                    <span className="rounded-lg border border-stone-700 px-2 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-stone-400">
                      {item.provider || "mock"}
                    </span>
                  </div>
                  <h4 className="mt-2 truncate text-base font-semibold text-stone-950">
                    {item.publication?.title || item.subject || "Edicao premium"}
                  </h4>
                  <p className="mt-1 max-w-3xl text-xs leading-5 text-stone-500">
                    {item.previewText || item.publication?.subtitle || "Entrega premium registrada pelo Distribution Engine."}
                  </p>
                </div>
                <div className="grid gap-2 text-xs text-stone-500 sm:grid-cols-4 xl:min-w-[32rem]">
                  <div className="rounded-lg border border-stone-700 bg-black/20 p-2">
                    <p className="font-semibold text-stone-400">Recebida</p>
                    <p>{formatDateTime(item.deliveredAt || item.sentAt)}</p>
                  </div>
                  <div className="rounded-lg border border-stone-700 bg-black/20 p-2">
                    <p className="font-semibold text-stone-400">Aberta</p>
                    <p>{formatDateTime(item.openedAt)}</p>
                  </div>
                  <div className="rounded-lg border border-stone-700 bg-black/20 p-2">
                    <p className="font-semibold text-stone-400">Baixada</p>
                    <p>{formatDateTime(item.lastDownloadAt)}</p>
                  </div>
                  <button
                    type="button"
                    className={item.canDownload ? "btn-primary h-full min-h-10 px-3 text-xs" : "btn-secondary h-full min-h-10 px-3 text-xs"}
                    disabled={!item.artifact || !item.canDownload || busyId === item.artifact?.id}
                    onClick={() => downloadArtifact(item.artifact)}
                    title={item.canDownload ? "Baixar PDF desta entrega" : "Seu plano atual nao permite baixar este PDF"}
                  >
                    {item.canDownload ? <Download size={15} /> : <Lock size={15} />}
                    {busyId === item.artifact?.id ? "Baixando..." : item.downloaded ? "Baixar novamente" : "Baixar"}
                  </button>
                </div>
              </div>
              {item.errorMessage ? <p className="mt-2 text-xs font-semibold text-rose-300">{item.errorMessage}</p> : null}
            </article>
          ))}
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="flex flex-col gap-2 border-b border-stone-700 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="font-semibold text-stone-950">Assinatura premium</h3>
            <p className="mt-1 text-xs text-stone-500">
              Gateway ativo: {billing?.provider || "mock"} ({billing?.providerMode === "test" ? "ambiente de teste" : "ambiente externo"}).
            </p>
          </div>
          {activeSubscription ? (
            <span className="inline-flex items-center gap-2 rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-xs font-bold uppercase tracking-[0.1em] text-emerald-300">
              <CheckCircle2 size={15} />
              Plano ativo
            </span>
          ) : null}
        </div>
        <div className="grid gap-3 p-4 xl:grid-cols-3">
          {plans
            .filter((plan) => Number(plan.monthlyPrice || 0) > 0)
            .map((plan) => (
              <article key={plan.code} className="rounded-lg border border-stone-700 bg-black/20 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-amber-300">{plan.tier}</p>
                    <h4 className="mt-1 text-lg font-semibold text-stone-950">{plan.name}</h4>
                  </div>
                  <CreditCard size={18} className="text-amber-300" />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <div className="rounded-lg border border-stone-700 p-3">
                    <p className="text-xs text-stone-500">Mensal</p>
                    <p className="mt-1 text-xl font-semibold text-stone-950">{formatMoney(plan.monthlyPrice, plan.currency)}</p>
                  </div>
                  <div className="rounded-lg border border-stone-700 p-3">
                    <p className="text-xs text-stone-500">Anual</p>
                    <p className="mt-1 text-xl font-semibold text-stone-950">{formatMoney(plan.annualPrice, plan.currency)}</p>
                  </div>
                </div>
                <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <button
                    type="button"
                    className="btn-primary h-9 flex-1 text-xs"
                    disabled={busyId === `${plan.code}:monthly`}
                    onClick={() => startCheckout(plan, "monthly")}
                  >
                    <CreditCard size={15} />
                    {busyId === `${plan.code}:monthly` ? "Processando..." : "Assinar mensal"}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary h-9 flex-1 text-xs"
                    disabled={busyId === `${plan.code}:annual`}
                    onClick={() => startCheckout(plan, "annual")}
                  >
                    {busyId === `${plan.code}:annual` ? "Processando..." : "Assinar anual"}
                  </button>
                </div>
                <p className="mt-3 text-xs leading-5 text-stone-500">
                  {plan.features?.length || 0} recurso(s), limite de {plan.limits?.pdfDownloadsPerPeriod || 0} download(s) de PDF por periodo.
                </p>
              </article>
            ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(22rem,0.6fr)]">
        <div className="surface overflow-hidden">
          <div className="border-b border-stone-700 px-4 py-3">
            <h3 className="font-semibold text-stone-950">Edicoes premium</h3>
            <p className="mt-1 text-xs text-stone-500">Somente publicacoes aprovadas ou publicadas aparecem para assinantes.</p>
          </div>
          <div className="divide-y divide-stone-800">
            {(data?.editions || []).length === 0 ? (
              <div className="p-4 text-sm text-stone-500">Ainda nao existe edicao premium aprovada para exibir.</div>
            ) : null}
            {(data?.editions || []).map((edition) => (
              <article key={edition.id} className="p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-2 py-1 text-[0.68rem] font-bold uppercase tracking-[0.12em] text-amber-300">
                        {edition.period}
                      </span>
                      <span className="rounded-lg border border-stone-700 px-2 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-stone-400">
                        {statusText(edition.status)}
                      </span>
                    </div>
                    <h4 className="mt-2 text-lg font-semibold text-stone-950">{edition.title}</h4>
                    <p className="mt-1 max-w-3xl text-sm leading-6 text-stone-500">{edition.subtitle || "Edicao premium aprovada para assinantes."}</p>
                  </div>
                  <div className="text-left text-xs text-stone-500 lg:text-right">
                    <p>Versao {edition.version}</p>
                    <p>Confianca {Math.round(Number(edition.confidence || 0))}/100</p>
                    <p>{formatDate(edition.publishedAt || edition.createdAt)}</p>
                  </div>
                </div>

                <div className="mt-3 grid gap-2">
                  {edition.pdfArtifacts.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-stone-700 p-3 text-sm text-stone-500">PDF ainda nao gerado para esta edicao.</div>
                  ) : null}
                  {edition.pdfArtifacts.map((artifact) => (
                    <div key={artifact.id} className="flex flex-col gap-3 rounded-lg border border-stone-700 bg-black/20 p-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-stone-950">{artifact.title || "PDF Premium"}</p>
                        <p className="mt-1 text-xs text-stone-500">
                          {artifact.pageCount || 0} pagina(s) | {Math.round(Number(artifact.contentSizeBytes || 0) / 1024)} KB | hash {String(artifact.artifactHash || "").slice(0, 10)}
                        </p>
                      </div>
                      <button
                        type="button"
                        className={artifact.canDownload ? "btn-primary h-9 px-3 text-xs" : "btn-secondary h-9 px-3 text-xs"}
                        disabled={!artifact.canDownload || busyId === artifact.id}
                        onClick={() => downloadArtifact(artifact)}
                        title={artifact.canDownload ? "Baixar PDF premium" : "Seu plano atual nao permite baixar este PDF"}
                      >
                        {artifact.canDownload ? <Download size={15} /> : <Lock size={15} />}
                        {busyId === artifact.id ? "Baixando..." : artifact.canDownload ? "Baixar PDF" : "Bloqueado"}
                      </button>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>

        <aside className="space-y-4">
          <div className="surface p-4">
            <div className="flex items-center gap-2">
              <TicketCheck size={17} className="text-amber-300" />
              <h3 className="font-semibold text-stone-950">Permissoes ativas</h3>
            </div>
            <div className="mt-3 grid gap-2">
              {activeEntitlements.length === 0 ? <p className="text-sm text-stone-500">Nenhuma permissao premium ativa.</p> : null}
              {activeEntitlements.map((item) => (
                <div key={item.id} className="rounded-lg border border-stone-700 bg-black/20 p-3">
                  <p className="text-sm font-semibold text-stone-950">{entitlementLabel(item.entitlementKey)}</p>
                  <p className="mt-1 text-xs text-stone-500">
                    Uso {item.usageCount || 0}
                    {item.usageLimit ? `/${item.usageLimit}` : ""} | expira {formatDate(item.expiresAt)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="surface p-4">
            <h3 className="font-semibold text-stone-950">Historico recente</h3>
            <div className="mt-3 grid gap-2">
              {(data?.recentAccessLogs || []).length === 0 ? <p className="text-sm text-stone-500">Nenhum acesso premium registrado ainda.</p> : null}
              {(data?.recentAccessLogs || []).slice(0, 8).map((log) => (
                <div key={log.id} className="rounded-lg border border-stone-700 bg-black/20 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.1em] text-stone-400">{log.action || "acesso"}</p>
                    <span className={log.allowed ? "text-xs font-bold text-emerald-300" : "text-xs font-bold text-rose-300"}>
                      {log.allowed ? "permitido" : "negado"}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-stone-500">{statusText(log.reason)} | {formatDate(log.createdAt)}</p>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
