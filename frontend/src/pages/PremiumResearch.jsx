import {
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  Mail,
  RefreshCw,
  Send,
  ShieldAlert,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import StatCard from "../components/StatCard.jsx";
import { apiFetch } from "../lib/api.js";

const currentPeriod = new Date().toISOString().slice(0, 7);

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-BR");
}

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function statusTone(status) {
  if (["approved", "reviewed", "ready_for_review", "ready_for_approval", "approved_for_review", "pass"].includes(status)) {
    return "border-emerald-400/35 bg-emerald-500/10 text-emerald-200";
  }
  if (["blocked", "block", "data_pending", "request_changes", "fail"].includes(status)) {
    return "border-rose-400/35 bg-rose-500/10 text-rose-200";
  }
  return "border-amber-400/35 bg-amber-500/10 text-amber-200";
}

function StatusBadge({ value }) {
  return (
    <span className={`inline-flex items-center rounded-lg border px-2.5 py-1 text-[0.68rem] font-bold uppercase tracking-[0.08em] ${statusTone(value)}`}>
      {String(value || "sem status").replaceAll("_", " ")}
    </span>
  );
}

function EmptyBox({ label }) {
  return <div className="rounded-lg border border-dashed border-stone-700 p-4 text-sm text-stone-500">{label}</div>;
}

export default function PremiumResearch({ token }) {
  const [publications, setPublications] = useState([]);
  const [detail, setDetail] = useState(null);
  const [version, setVersion] = useState(null);
  const [committee, setCommittee] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [period, setPeriod] = useState(currentPeriod);
  const [title, setTitle] = useState(`Alpha Premium Research - ${currentPeriod}`);
  const [reviewComment, setReviewComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const latestVersion = useMemo(() => detail?.versions?.[0] || null, [detail]);
  const activeVersionId = selectedVersionId || latestVersion?.id || "";
  const latestCommittee = useMemo(() => detail?.committeeRuns?.[0] || null, [detail]);
  const latestReview = detail?.reviews?.[0] || null;
  const latestApproval = detail?.approvals?.[0] || null;
  const latestPdfArtifact = useMemo(() => (detail?.artifacts || []).find((item) => item.artifactType === "pdf" || item.contentType === "application/pdf") || null, [detail]);
  const publicationCampaigns = useMemo(() => campaigns.filter((item) => item.publicationId === selectedId), [campaigns, selectedId]);
  const latestCampaign = publicationCampaigns[0] || null;
  const readiness = version?.payload?.readiness || {};
  const readinessGates = readiness.gates || [];
  const committeeGates = committee?.gates || [];
  const committeeVotes = committee?.votes || [];
  const canApprove = latestReview?.decision === "approve" && latestCommittee && latestCommittee.decision !== "blocked" && number(latestCommittee.blockerCount) === 0;

  async function loadPublications(nextSelectedId = selectedId) {
    setLoading(true);
    setError("");
    try {
      const listing = await apiFetch("/premium/publications?limit=40", { token });
      const campaignListing = await apiFetch("/distribution/campaigns?limit=80", { token });
      const items = listing.items || [];
      setPublications(items);
      setCampaigns(campaignListing.items || []);
      const chosen = nextSelectedId || items[0]?.id || "";
      setSelectedId(chosen);
      if (chosen) {
        await loadDetail(chosen);
      } else {
        setDetail(null);
        setVersion(null);
        setCommittee(null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(publicationId, versionId = "") {
    const publication = await apiFetch(`/premium/publications/${publicationId}`, { token });
    setDetail(publication);
    const targetVersionId = versionId || publication.versions?.[0]?.id || "";
    setSelectedVersionId(targetVersionId);
    if (targetVersionId) {
      const versionPayload = await apiFetch(`/premium/publications/${publicationId}/versions/${targetVersionId}`, { token });
      setVersion(versionPayload);
    } else {
      setVersion(null);
    }
    const runId = publication.committeeRuns?.[0]?.id;
    if (runId) {
      const run = await apiFetch(`/premium/committee/runs/${runId}`, { token });
      setCommittee(run);
    } else {
      setCommittee(null);
    }
  }

  async function runAction(label, action) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await action();
      setNotice(label);
      return result;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function createDraft() {
    const result = await runAction("Rascunho premium criado.", () =>
      apiFetch("/premium/publications/drafts", {
        method: "POST",
        token,
        body: {
          period,
          title: title || `Alpha Premium Research - ${period || currentPeriod}`,
          publication_type: "monthly_research",
          refresh_market: false,
        },
      })
    );
    if (result?.id) {
      await loadPublications(result.id);
    }
  }

  async function syncTheses() {
    if (!selectedId) return;
    await runAction("Teses versionadas sincronizadas.", () =>
      apiFetch(`/premium/publications/${selectedId}/theses/sync`, {
        method: "POST",
        token,
        body: { publication_version_id: activeVersionId, force_new_version: true, refresh_market: false },
      })
    );
    await loadDetail(selectedId, activeVersionId);
  }

  async function syncRatings() {
    if (!selectedId) return;
    await runAction("Ratings sincronizados e comite atualizado.", () =>
      apiFetch(`/premium/publications/${selectedId}/ratings/sync`, {
        method: "POST",
        token,
        body: { publication_version_id: activeVersionId, force_new_version: true, run_committee: true },
      })
    );
    await loadDetail(selectedId, activeVersionId);
  }

  async function runCommittee() {
    if (!selectedId) return;
    await runAction("Research Committee executado.", () =>
      apiFetch(`/premium/publications/${selectedId}/committee/run`, {
        method: "POST",
        token,
        body: { publication_version_id: activeVersionId },
      })
    );
    await loadDetail(selectedId, activeVersionId);
  }

  async function recordReview(decision) {
    if (!selectedId) return;
    await runAction(decision === "approve" ? "Revisao humana aprovada." : "Alteracoes solicitadas.", () =>
      apiFetch(`/premium/publications/${selectedId}/reviews`, {
        method: "POST",
        token,
        body: {
          publication_version_id: activeVersionId,
          decision,
          comments: reviewComment,
          requested_changes: decision === "request_changes" && reviewComment ? [reviewComment] : [],
        },
      })
    );
    setReviewComment("");
    await loadPublications(selectedId);
  }

  async function recordApproval(decision) {
    if (!selectedId) return;
    await runAction(decision === "approve_publication" ? "Publicacao aprovada para proxima etapa." : "Publicacao rejeitada.", () =>
      apiFetch(`/premium/publications/${selectedId}/approvals`, {
        method: "POST",
        token,
        body: {
          publication_version_id: activeVersionId,
          decision,
          comments: reviewComment,
        },
      })
    );
    setReviewComment("");
    await loadPublications(selectedId);
  }

  async function createDistributionCampaign() {
    if (!selectedId) return;
    const result = await runAction("Campanha de distribuicao criada.", () =>
      apiFetch("/distribution/campaigns", {
        method: "POST",
        token,
        body: {
          publication_id: selectedId,
          artifact_id: latestPdfArtifact?.id || null,
          channel: "email",
          audience_type: "premium_subscribers",
          subject: detail?.title || "Carteira Alpha Premium",
          preview_text: detail?.subtitle || "Nova edicao premium disponivel para assinantes.",
        },
      })
    );
    if (result?.id) {
      const campaignListing = await apiFetch("/distribution/campaigns?limit=80", { token });
      setCampaigns(campaignListing.items || []);
    }
  }

  async function dispatchDistributionCampaign(campaignId) {
    if (!campaignId) return;
    const result = await runAction("Campanha enviada pelo Distribution Engine.", () =>
      apiFetch(`/distribution/campaigns/${campaignId}/dispatch`, {
        method: "POST",
        token,
      })
    );
    if (result?.id) {
      const campaignListing = await apiFetch("/distribution/campaigns?limit=80", { token });
      setCampaigns(campaignListing.items || []);
    }
  }

  useEffect(() => {
    loadPublications("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (loading && !detail) return <LoadingState label="Carregando Alpha Premium Research..." />;

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Research Premium</p>
          <h2 className="text-2xl font-semibold text-stone-950">Centro editorial Alpha</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
            Controle os rascunhos premium, teses, ratings e gates do Research Committee antes de qualquer publicacao.
          </p>
        </div>
        <button type="button" className="btn-secondary h-10 px-4 text-sm" onClick={() => loadPublications(selectedId)} disabled={busy || loading}>
          <RefreshCw size={16} />
          Atualizar
        </button>
      </header>

      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="rounded-lg border border-emerald-400/25 bg-emerald-500/10 px-4 py-3 text-sm font-semibold text-emerald-200">{notice}</div> : null}

      <section className="grid gap-3 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <div className="surface p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-amber-400/35 bg-amber-500/10 text-amber-300">
              <Sparkles size={17} />
            </div>
            <div>
              <h3 className="font-semibold text-stone-950">Criar edicao premium</h3>
              <p className="mt-1 text-xs leading-5 text-stone-500">Gera um rascunho versionado com fontes, evidencias, teses, ratings e comite. Nao publica automaticamente.</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-[10rem_minmax(0,1fr)]">
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">
              Mes
              <input className="field mt-1" value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2026-07" />
            </label>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">
              Titulo
              <input className="field mt-1" value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>
          </div>
          <button type="button" className="btn-primary mt-4 h-10 w-full text-sm" onClick={createDraft} disabled={busy}>
            <FileSearch size={16} />
            Criar rascunho
          </button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Publicacoes" value={publications.length} hint="Rascunhos e edicoes premium." icon={FileSearch} tone="amber" compact />
          <StatCard label="Readiness" value={`${Math.round(number(version?.readinessScore || readiness.score))}/100`} hint={version?.readinessClassification || readiness.classification || "sem versao"} icon={ClipboardCheck} tone="emerald" compact />
          <StatCard label="Comite" value={latestCommittee?.decision ? String(latestCommittee.decision).replaceAll("_", " ") : "-"} hint={`${latestCommittee?.blockerCount || 0} bloqueios, ${latestCommittee?.warningCount || 0} alertas`} icon={ShieldAlert} tone={latestCommittee?.decision === "blocked" ? "rose" : "amber"} compact />
          <StatCard label="Aprovacao" value={detail?.status || "-"} hint={latestApproval?.decision || "Aguardando decisao humana."} icon={CheckCircle2} tone={detail?.status === "approved" ? "emerald" : "stone"} compact />
          <StatCard label="Distribuicao" value={campaigns.length} hint="Campanhas premium criadas." icon={Mail} tone="sky" compact />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[20rem_minmax(0,1fr)]">
        <div className="surface overflow-hidden">
          <div className="border-b border-stone-200 p-4">
            <h3 className="font-semibold text-stone-950">Edicoes</h3>
            <p className="mt-1 text-xs text-stone-500">Selecione uma publicacao para revisar.</p>
          </div>
          <div className="max-h-[36rem] overflow-y-auto">
            {publications.length === 0 ? <div className="p-4"><EmptyBox label="Nenhum rascunho premium criado ainda." /></div> : null}
            {publications.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={async () => {
                  setSelectedId(item.id);
                  await loadDetail(item.id);
                }}
                className={`block w-full border-b border-stone-200 p-4 text-left transition hover:bg-white/5 ${selectedId === item.id ? "bg-amber-500/10" : ""}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-stone-950">{item.title}</p>
                    <p className="mt-1 text-xs text-stone-500">{item.period} | {item.currentVersion}</p>
                  </div>
                  <StatusBadge value={item.status} />
                </div>
                <p className="mt-2 text-xs leading-5 text-stone-500">
                  Readiness {Math.round(number(item.readinessScore || item.confidence))}/100 | {item.sectionCount || 0} secoes | {item.evidenceCount || 0} evidencias
                </p>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {!detail ? <EmptyBox label="Crie ou selecione uma edicao premium para comecar." /> : null}
          {detail ? (
            <>
              <div className="surface p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Edicao selecionada</p>
                    <h3 className="mt-1 text-xl font-semibold text-stone-950">{detail.title}</h3>
                    <p className="mt-1 text-sm text-stone-500">{detail.subtitle || "Rascunho editorial em preparacao."}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge value={detail.status} />
                    <StatusBadge value={version?.readinessClassification} />
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <div className="rounded-lg border border-stone-200 p-3">
                    <p className="text-xs uppercase tracking-[0.12em] text-stone-500">Versao ativa</p>
                    <select
                      className="field mt-2"
                      value={activeVersionId}
                      onChange={async (event) => {
                        setSelectedVersionId(event.target.value);
                        await loadDetail(selectedId, event.target.value);
                      }}
                    >
                      {(detail.versions || []).map((item) => (
                        <option key={item.id} value={item.id}>{item.version} - {item.status}</option>
                      ))}
                    </select>
                  </div>
                  <div className="rounded-lg border border-stone-200 p-3">
                    <p className="text-xs uppercase tracking-[0.12em] text-stone-500">Ultima revisao</p>
                    <p className="mt-2 text-sm font-semibold text-stone-950">{latestReview?.decision || "Sem revisao humana"}</p>
                    <p className="mt-1 text-xs text-stone-500">{formatDate(latestReview?.createdAt)}</p>
                  </div>
                  <div className="rounded-lg border border-stone-200 p-3">
                    <p className="text-xs uppercase tracking-[0.12em] text-stone-500">Ultima aprovacao</p>
                    <p className="mt-2 text-sm font-semibold text-stone-950">{latestApproval?.decision || "Sem decisao final"}</p>
                    <p className="mt-1 text-xs text-stone-500">{formatDate(latestApproval?.createdAt)}</p>
                  </div>
                </div>
              </div>

              <div className="surface p-4">
                <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                  <div>
                    <h3 className="font-semibold text-stone-950">Fluxo operacional</h3>
                    <p className="mt-1 text-xs text-stone-500">Use de cima para baixo: tese, rating, comite, revisao humana e aprovacao.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button className="btn-secondary h-9 px-3 text-xs" onClick={syncTheses} disabled={busy}><RefreshCw size={14} />Teses</button>
                    <button className="btn-secondary h-9 px-3 text-xs" onClick={syncRatings} disabled={busy}><RefreshCw size={14} />Ratings + comite</button>
                    <button className="btn-secondary h-9 px-3 text-xs" onClick={runCommittee} disabled={busy}><ShieldAlert size={14} />Rodar comite</button>
                  </div>
                </div>
                <textarea
                  className="field mt-4 min-h-24"
                  value={reviewComment}
                  onChange={(event) => setReviewComment(event.target.value)}
                  placeholder="Comentario humano para revisao, mudancas ou aprovacao."
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  <button className="btn-secondary h-9 px-3 text-xs" onClick={() => recordReview("request_changes")} disabled={busy}>
                    <XCircle size={14} />
                    Solicitar ajustes
                  </button>
                  <button className="btn-secondary h-9 px-3 text-xs" onClick={() => recordReview("approve")} disabled={busy}>
                    <CheckCircle2 size={14} />
                    Aprovar revisao
                  </button>
                  <button className="btn-secondary h-9 px-3 text-xs" onClick={() => recordApproval("reject_publication")} disabled={busy}>
                    <XCircle size={14} />
                    Rejeitar final
                  </button>
                  <button className="btn-primary h-9 px-3 text-xs" onClick={() => recordApproval("approve_publication")} disabled={busy || !canApprove}>
                    <CheckCircle2 size={14} />
                    Aprovar publicacao
                  </button>
                </div>
                {!canApprove ? (
                  <p className="mt-3 rounded-lg border border-amber-400/25 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-200">
                    Aprovacao final fica bloqueada enquanto nao houver revisao humana aprovada e comite sem bloqueios.
                  </p>
                ) : null}
              </div>

              <section className="surface overflow-hidden">
                <div className="flex flex-col gap-3 border-b border-stone-200 p-4 xl:flex-row xl:items-center xl:justify-between">
                  <div>
                    <h3 className="font-semibold text-stone-950">Distribution Engine</h3>
                    <p className="mt-1 text-xs text-stone-500">
                      Cria campanha para assinantes premium ativos. O provider atual e mock, entao o envio fica auditado sem disparar email real.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      className="btn-secondary h-9 px-3 text-xs"
                      onClick={createDistributionCampaign}
                      disabled={busy || detail.status !== "approved" || !latestPdfArtifact}
                      title={!latestPdfArtifact ? "Gere o PDF da edicao antes de distribuir" : "Criar campanha para assinantes premium"}
                    >
                      <Mail size={14} />
                      Criar campanha
                    </button>
                    <button
                      className="btn-primary h-9 px-3 text-xs"
                      onClick={() => dispatchDistributionCampaign(latestCampaign?.id)}
                      disabled={busy || !latestCampaign || ["sent", "completed"].includes(latestCampaign.status)}
                    >
                      <Send size={14} />
                      Disparar
                    </button>
                  </div>
                </div>
                <div className="divide-y divide-stone-200">
                  {publicationCampaigns.length === 0 ? (
                    <div className="p-4">
                      <EmptyBox label={latestPdfArtifact ? "Nenhuma campanha criada para esta edicao." : "Gere um PDF aprovado antes de criar a campanha."} />
                    </div>
                  ) : null}
                  {publicationCampaigns.map((campaign) => (
                    <div key={campaign.id} className="p-4">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <p className="font-semibold text-stone-950">{campaign.subject || campaign.name}</p>
                          <p className="mt-1 text-xs text-stone-500">
                            {campaign.channel} | {campaign.audienceType} | {campaign.provider} | {formatDate(campaign.createdAt)}
                          </p>
                        </div>
                        <StatusBadge value={campaign.status} />
                      </div>
                      <div className="mt-3 grid gap-2 sm:grid-cols-4">
                        <div className="rounded-lg border border-stone-200 p-3">
                          <p className="text-xs text-stone-500">Destinatarios</p>
                          <p className="mt-1 font-semibold text-stone-950">{campaign.recipientCount}</p>
                        </div>
                        <div className="rounded-lg border border-stone-200 p-3">
                          <p className="text-xs text-stone-500">Entregues</p>
                          <p className="mt-1 font-semibold text-emerald-300">{campaign.deliveredCount}</p>
                        </div>
                        <div className="rounded-lg border border-stone-200 p-3">
                          <p className="text-xs text-stone-500">Falhas</p>
                          <p className="mt-1 font-semibold text-rose-300">{campaign.failedCount}</p>
                        </div>
                        <div className="rounded-lg border border-stone-200 p-3">
                          <p className="text-xs text-stone-500">Aberturas</p>
                          <p className="mt-1 font-semibold text-stone-950">{campaign.openCount}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="grid gap-4 xl:grid-cols-2">
                <div className="surface overflow-hidden">
                  <div className="border-b border-stone-200 p-4">
                    <h3 className="font-semibold text-stone-950">Readiness da edicao</h3>
                    <p className="mt-1 text-xs text-stone-500">Gates do Publisher antes da revisao editorial.</p>
                  </div>
                  <div className="divide-y divide-stone-200">
                    {readinessGates.length === 0 ? <div className="p-4"><EmptyBox label="Sem gates de readiness nesta versao." /></div> : null}
                    {readinessGates.map((gate) => (
                      <div key={gate.id || gate.title} className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <p className="font-semibold text-stone-950">{gate.title}</p>
                          <StatusBadge value={gate.status} />
                        </div>
                        <p className="mt-2 text-xs leading-5 text-stone-500">{gate.reading}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="surface overflow-hidden">
                  <div className="border-b border-stone-200 p-4">
                    <h3 className="font-semibold text-stone-950">Research Committee</h3>
                    <p className="mt-1 text-xs text-stone-500">Decisao automatica que antecede a revisao humana.</p>
                  </div>
                  <div className="p-4">
                    {committee ? (
                      <>
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <StatusBadge value={committee.decision} />
                          <p className="text-sm font-semibold text-stone-950">{Math.round(number(committee.approvalScore))}/100</p>
                        </div>
                        <p className="mt-3 text-sm leading-6 text-stone-500">{committee.summary}</p>
                      </>
                    ) : (
                      <EmptyBox label="Nenhuma rodada do comite encontrada." />
                    )}
                  </div>
                  <div className="divide-y divide-stone-200">
                    {committeeGates.slice(0, 8).map((gate) => (
                      <div key={gate.id} className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <p className="font-semibold text-stone-950">{gate.title}</p>
                          <StatusBadge value={gate.status} />
                        </div>
                        <p className="mt-2 text-xs leading-5 text-stone-500">{gate.reading}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              <section className="surface overflow-hidden">
                <div className="border-b border-stone-200 p-4">
                  <h3 className="font-semibold text-stone-950">Secoes da versao</h3>
                  <p className="mt-1 text-xs text-stone-500">Cada bloco precisa estar estruturado e rastreavel antes da publicacao.</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="premium-table min-w-full text-left text-sm">
                    <thead>
                      <tr>
                        <th>Secao</th>
                        <th>Status</th>
                        <th>Confianca</th>
                        <th>Evidencias</th>
                        <th>Revisao humana</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(version?.sections || []).map((section) => (
                        <tr key={section.id}>
                          <td>
                            <p className="font-semibold text-stone-950">{section.title}</p>
                            <p className="text-xs text-stone-500">{section.key}</p>
                          </td>
                          <td><StatusBadge value={section.status} /></td>
                          <td>{Math.round(number(section.confidence))}/100</td>
                          <td>{section.evidenceIds?.length || 0}</td>
                          <td>{section.requiresHumanApproval ? "Obrigatoria" : "Nao exigida"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="surface overflow-hidden">
                <div className="border-b border-stone-200 p-4">
                  <h3 className="font-semibold text-stone-950">Votos do comite</h3>
                  <p className="mt-1 text-xs text-stone-500">Mostra a leitura de cada motor antes da decisao final.</p>
                </div>
                <div className="divide-y divide-stone-200">
                  {committeeVotes.length === 0 ? <div className="p-4"><EmptyBox label="Sem votos detalhados nesta rodada." /></div> : null}
                  {committeeVotes.map((vote) => (
                    <div key={vote.id} className="p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-stone-950">{String(vote.voterKey || "").replaceAll("_", " ")}</p>
                          <p className="mt-1 text-xs text-stone-500">Confianca {Math.round(number(vote.confidence))}/100</p>
                        </div>
                        <StatusBadge value={vote.decision} />
                      </div>
                      <p className="mt-2 text-xs leading-5 text-stone-500">{vote.rationale}</p>
                    </div>
                  ))}
                </div>
              </section>
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
}
