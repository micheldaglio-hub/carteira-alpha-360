import { AlertTriangle, BarChart3, BookOpenCheck, Flame, Globe2, LineChart, Newspaper, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart as ReLineChart,
  Pie,
  PieChart as RePieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import StatCard from "../components/StatCard.jsx";
import { apiFetch } from "../lib/api.js";
import { currency, pct } from "../lib/format.js";

const axisTick = { fontSize: 11, fill: "var(--muted)" };
const tooltipStyle = { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)" };
const tooltipLabelStyle = { color: "var(--primary)" };
const usd = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", maximumFractionDigits: 6 });
const today = new Date().toISOString().slice(0, 10);
const defaultGlobalBacktestStart = "2025-01-01";
const sectorTooltipStyle = {
  background: "rgba(245, 200, 75, 0.96)",
  border: "1px solid rgba(245, 200, 75, 0.7)",
  borderRadius: 8,
  color: "#09090b",
  boxShadow: "0 12px 30px rgba(0, 0, 0, 0.24)",
  fontSize: 12,
  padding: "0.45rem 0.6rem",
};
const sectorTooltipLabelStyle = { color: "#09090b", fontWeight: 800 };
const palette = ["#f5c84b", "#3bd19f", "#74c7ff", "#f97373", "#a78bfa", "#f59e0b"];

function RiskBadge({ value }) {
  const normalized = String(value || "").replaceAll("_", " ");
  const cls = value?.includes("alto") || value === "extremo"
    ? "border-rose-400/40 bg-rose-500/10 text-rose-300"
    : "border-amber-400/40 bg-amber-500/10 text-amber-300";
  return <span className={`rounded-lg border px-2.5 py-1 text-[0.72rem] font-semibold uppercase ${cls}`}>{normalized}</span>;
}

function alphaConviction(asset, validationRow) {
  const score = Number(validationRow?.validationScore || 0);
  if (score >= 72) return "Nucleo Alpha";
  if (asset.targetWeight >= 12) return "Pilar da carteira";
  if (score >= 50) return "Posicao estrategica";
  return "Peso controlado";
}

function alphaThesis(asset, validationRow) {
  const score = Number(validationRow?.validationScore || 0);
  if (score >= 72) {
    return `${asset.ticker} entra como ativo de alta conviccao para renda passiva, combinando setor perene, proventos e leitura quantitativa favoravel.`;
  }
  if (asset.sector === "Bancos") {
    return `${asset.ticker} compoe a carteira pelo peso estrutural dos bancos no Brasil, potencial de geracao de caixa e historico de distribuicao de resultados.`;
  }
  if (asset.sector === "Energia") {
    return `${asset.ticker} compoe a carteira pela previsibilidade do setor eletrico, contratos regulados e papel defensivo em uma estrategia de proventos.`;
  }
  if (asset.sector === "Saneamento") {
    return `${asset.ticker} compoe a carteira por atuar em servico essencial, com demanda resiliente e perfil adequado para preservacao patrimonial.`;
  }
  if (asset.sector === "Seguros") {
    return `${asset.ticker} compoe a carteira pela rentabilidade do setor de seguros, geracao de caixa e exposicao positiva a juros elevados.`;
  }
  return asset.thesis;
}

function confidenceClass(status) {
  if (status === "ok") return "border-emerald-400/30 bg-emerald-500/10 text-emerald-200";
  if (status === "blocker") return "border-rose-400/30 bg-rose-500/10 text-rose-200";
  return "border-amber-400/30 bg-amber-500/10 text-amber-200";
}

function scoreLabel(key) {
  const labels = {
    corePortfolio: "Carteira principal",
    fiiSatellite: "FIIs",
    globalSatellite: "Exterior",
    cryptoSatellite: "Cripto",
    confidence: "Confianca dos dados",
    methodology: "Metodologia",
    diversification: "Diversificacao",
    evidence: "Evidencias",
    monthlyGovernance: "Revisao mensal",
  };
  return labels[key] || String(key).replace(/([A-Z])/g, " $1");
}

function scoreHelp(key) {
  const help = {
    corePortfolio: "Qualidade da carteira principal de acoes brasileiras.",
    fiiSatellite: "Qualidade inicial da parte de fundos imobiliarios.",
    globalSatellite: "Qualidade da diversificacao internacional.",
    cryptoSatellite: "Qualidade da cripto do mes como satelite de alto risco.",
    confidence: "Quanto o Alpha confia nos dados usados para calcular a carteira.",
    methodology: "Disciplina do processo: screener, criterios, pesos e revisao.",
    diversification: "Se a carteira esta espalhada entre setores, classes e ativos.",
    evidence: "Quantidade e qualidade das evidencias disponiveis.",
    monthlyGovernance: "Se existe rotina de revisao e acompanhamento mensal.",
  };
  return help[key] || "Componente usado para formar a nota do relatorio.";
}

export default function ModelPortfolios({ token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [validating, setValidating] = useState(false);
  const [globalBacktest, setGlobalBacktest] = useState(null);
  const [globalBacktestForm, setGlobalBacktestForm] = useState({
    start_date: defaultGlobalBacktestStart,
    end_date: today,
    initial_value: 1000,
  });
  const [globalBacktestLoading, setGlobalBacktestLoading] = useState(false);
  const [globalBacktestError, setGlobalBacktestError] = useState("");
  const [researchCenter, setResearchCenter] = useState(null);

  useEffect(() => {
    setData(null);
    setError("");
    apiFetch("/model-portfolios", { token })
      .then(setData)
      .catch((err) => setError(err.message));
    apiFetch("/wealth-os/research?limit=8", { token })
      .then(setResearchCenter)
      .catch(() => setResearchCenter(null));
  }, [token]);

  const sortedAssets = useMemo(
    () => [...(data?.dividendPortfolio?.assets || [])].sort((a, b) => b.targetWeight - a.targetWeight),
    [data]
  );
  const validation = data?.validation || {};
  const validationByTicker = useMemo(() => {
    const rows = validation.rows || [];
    return Object.fromEntries(rows.map((row) => [row.ticker, row]));
  }, [validation.rows]);
  const confidenceReport = data?.confidenceReport || {};
  const recommendedReport = data?.recommendedPortfolioReport || {};
  const recommendationGovernance = data?.recommendationGovernance || recommendedReport?.governanceLedgerV2 || {};
  const confidenceByTicker = useMemo(() => {
    const rows = confidenceReport.assetRows || [];
    return Object.fromEntries(rows.map((row) => [row.ticker, row]));
  }, [confidenceReport.assetRows]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  const summary = data.backtest.summary;
  const screener = data.screener || {};
  const fiiPortfolio = data.fiiPortfolio || {};
  const globalPortfolio = data.globalPortfolio || {};
  const activeGlobalBacktest = globalBacktest || data.globalBacktest || {};
  const globalBacktestRows = activeGlobalBacktest.rows || [];
  const globalBacktestVehicles = activeGlobalBacktest.vehicles || [];
  const cryptoReport = data.cryptoStudy.researchReport || {};
  const researchReports = researchCenter?.reports || [];
  const researchNews = researchCenter?.newsFeed || [];

  async function validateWithAlpha() {
    setValidating(true);
    setError("");
    try {
      const result = await apiFetch("/model-portfolios/validate", { method: "POST", token });
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setValidating(false);
    }
  }

  async function runGlobalBacktest(refreshMarket = false) {
    setGlobalBacktestLoading(true);
    setGlobalBacktestError("");
    const params = new URLSearchParams({
      start_date: globalBacktestForm.start_date,
      end_date: globalBacktestForm.end_date || today,
      initial_value: String(globalBacktestForm.initial_value || 1000),
    });
    try {
      const result = await apiFetch(`/model-portfolios/global-backtest${refreshMarket ? "/run" : ""}?${params.toString()}`, {
        method: refreshMarket ? "POST" : "GET",
        token,
      });
      setGlobalBacktest(result);
    } catch (err) {
      setGlobalBacktestError(err.message);
    } finally {
      setGlobalBacktestLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Carteira recomendada</p>
          <h2 className="text-2xl font-semibold text-stone-950">Carteira Recomendada Alpha</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
            Carteira oficial gerada pelo Screener Alpha B3, com estudos separados para FIIs, cripto e diversificacao internacional.
          </p>
        </div>
        <div className="surface max-w-xl p-3 text-xs leading-5 text-stone-500">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold uppercase tracking-[0.14em] text-brand">Analise Alpha</p>
              <p className="mt-1">A carteira abaixo e a minha selecao principal para renda passiva e setores perenes.</p>
              <p className="mt-2 font-semibold text-stone-950">Use o botao para atualizar fundamentos, precos e leitura quantitativa.</p>
            </div>
            <button type="button" onClick={validateWithAlpha} className="btn-primary h-9 shrink-0 px-3 text-xs" disabled={validating}>
              <RefreshCw size={15} />
              {validating ? "Atualizando" : "Atualizar analise"}
            </button>
          </div>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <StatCard label="Carteira Alpha" value={`${screener.selectedCount || 10} ativos`} hint={data.dividendPortfolio.profile} icon={ShieldCheck} tone="amber" compact token={token} evidenceDomain="recommendation" evidenceField="institutionalScore" />
        <StatCard label="Screener B3" value={`${screener.candidateCount || 0} candidatas`} hint={`${screener.eligibleUniverseCount || 0} ativos elegiveis no universo B3.`} icon={Sparkles} tone="emerald" compact />
        <StatCard label="FIIs Alpha" value={`${fiiPortfolio.assets?.length || 0} fundos`} hint="Renda imobiliaria e proventos mensais." icon={BookOpenCheck} tone="sky" compact />
        <StatCard label="Global Alpha" value={`${globalPortfolio.assets?.length || 0} stocks`} hint="Diversificacao internacional em validacao." icon={Globe2} tone="emerald" compact />
        <StatCard label="Backtest referencia" value={pct(summary.stockTotalReturn)} hint={`${currency.format(summary.stockFinalValue)} no periodo historico importado.`} icon={LineChart} tone="amber" compact token={token} evidenceDomain="recommendation" evidenceField="scoreBreakdown.evidence" />
        <StatCard label="Cripto do mes" value={data.cryptoStudy.ticker} hint={data.cryptoStudy.decisionLabel || data.cryptoStudy.category} icon={BarChart3} tone="sky" compact />
      </section>

      {recommendedReport.status ? (
        <section className="surface overflow-hidden">
          <div className="border-b border-stone-200 bg-amber-500/10 px-4 py-3 text-sm leading-6 text-stone-600">
            <strong className="text-stone-950">Como ler esta pagina:</strong> a nota maior e a qualidade do relatorio da Carteira Recomendada Alpha.
            A nota de confianca mede apenas a qualidade dos dados disponiveis. Por isso uma pode ser 85/100 e a outra 79/100:
            a carteira pode ser bem montada, mas ainda existir algum dado externo pendente de validacao.
          </div>
          <div className="grid gap-4 border-b border-stone-200 p-4 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-amber-500" />
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">{recommendedReport.title}</p>
              </div>
              <p className="mt-2 text-3xl font-semibold text-stone-950">{Number(recommendedReport.institutionalScore || 0).toFixed(0)}/100</p>
              <p className="mt-1 text-sm font-semibold text-amber-300">{recommendedReport.classification}</p>
              <p className="mt-3 text-sm leading-6 text-stone-500">{recommendedReport.headline}</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Mes</p>
                  <p className="mt-1 text-sm font-semibold text-stone-950">{recommendedReport.reportMonth}</p>
                </div>
                <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Proxima revisao</p>
                  <p className="mt-1 text-sm font-semibold text-stone-950">{recommendedReport.nextReviewDate}</p>
                </div>
                <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Risco</p>
                  <p className="mt-1 text-sm font-semibold text-stone-950">{String(recommendedReport.riskLevel || "").replaceAll("_", " ")}</p>
                </div>
              </div>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {(recommendedReport.executiveSummary || []).map((item) => (
                <p key={item} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">
                  {item}
                </p>
              ))}
            </div>
          </div>

          <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">De onde vem a nota</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {Object.entries(recommendedReport.scoreBreakdown || {}).map(([key, value]) => (
                  <div key={key} className="rounded-lg border border-stone-200 bg-black/10 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.1em] text-stone-500">
                        {scoreLabel(key)}
                      </p>
                      <span className="text-sm font-semibold text-stone-950">{Number(value || 0).toFixed(0)}</span>
                    </div>
                    <div className="mt-2 h-1.5 rounded-full bg-stone-800">
                      <div className="h-1.5 rounded-full bg-brand" style={{ width: `${Math.max(2, Math.min(100, Number(value || 0)))}%` }} />
                    </div>
                    <p className="mt-2 text-[0.68rem] leading-4 text-stone-500">{scoreHelp(key)}</p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Principais ativos do relatorio</p>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {(recommendedReport.assetReports || []).slice(0, 6).map((asset) => (
                  <div key={`${asset.assetClass}-${asset.ticker}`} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-stone-950">{asset.ticker}</p>
                        <p className="text-xs text-stone-500">{asset.role}</p>
                      </div>
                      <span className="rounded-lg border border-amber-400/40 bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-300">
                        {Number(asset.institutionalScore || 0).toFixed(0)}
                      </span>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-stone-500">{asset.thesis}</p>
                    <p className="mt-2 text-[0.68rem] font-semibold uppercase tracking-[0.1em] text-stone-500">{asset.classification}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-4 border-t border-stone-200 p-4 xl:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Riscos monitorados</p>
              <div className="mt-3 grid gap-2">
                {(recommendedReport.riskMatrix || []).map((risk) => (
                  <div key={risk.id} className="rounded-lg border border-stone-200 bg-black/10 px-3 py-2">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-stone-950">{risk.title}</p>
                      <span className="text-xs font-semibold uppercase text-amber-300">{risk.severity}</span>
                    </div>
                    <p className="mt-1 text-xs leading-5 text-stone-500">{risk.reading}</p>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Revisao mensal</p>
              <div className="mt-3 grid gap-2">
                {(recommendedReport.monthlyReview?.checklist || []).slice(0, 5).map((item) => (
                  <p key={item} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">{item}</p>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {recommendationGovernance.status ? (
        <section className="surface overflow-hidden">
          <div className="grid gap-4 border-b border-stone-200 p-4 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div>
              <div className="flex items-center gap-2">
                <BookOpenCheck size={18} className="text-amber-500" />
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">{recommendationGovernance.title}</p>
              </div>
              <h3 className="mt-2 text-xl font-semibold text-stone-950">Governanca da recomendacao</h3>
              <p className="mt-2 text-sm leading-6 text-stone-500">
                Essa camada registra quando a carteira foi revisada, qual era a confianca dos dados e quais eventos exigem nova analise.
              </p>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Review</p>
                  <p className="mt-1 truncate text-sm font-semibold text-stone-950">{recommendationGovernance.reviewId}</p>
                </div>
                <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Proxima revisao</p>
                  <p className="mt-1 text-sm font-semibold text-stone-950">{recommendationGovernance.nextReviewDate}</p>
                </div>
                <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Status</p>
                  <p className="mt-1 text-sm font-semibold text-stone-950">{String(recommendationGovernance.status).replaceAll("_", " ")}</p>
                </div>
              </div>
            </div>
            <div className="grid gap-2 md:grid-cols-3">
              <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand">Score institucional</p>
                <p className="mt-2 text-2xl font-semibold text-stone-950">{Number(recommendationGovernance.institutionalScore || 0).toFixed(0)}/100</p>
                <p className="mt-1 text-xs leading-5 text-stone-500">Qualidade do relatorio e da carteira proposta.</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand">Confianca Alpha</p>
                <p className="mt-2 text-2xl font-semibold text-stone-950">{Number(recommendationGovernance.confidenceScore || 0).toFixed(0)}/100</p>
                <p className="mt-1 text-xs leading-5 text-stone-500">Confianca metodologica do relatorio.</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand">Dados do usuario</p>
                <p className="mt-2 text-2xl font-semibold text-stone-950">{Number(recommendationGovernance.dataConfidenceScore || 0).toFixed(0)}/100</p>
                <p className="mt-1 text-xs leading-5 text-stone-500">Rastreabilidade dos dados da sua carteira.</p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Trilha dos ativos</p>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {(recommendationGovernance.assetReviews || []).slice(0, 6).map((asset) => (
                  <div key={`${asset.assetClass}-${asset.ticker}`} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-stone-950">{asset.ticker}</p>
                        <p className="text-xs text-stone-500">{String(asset.reviewStatus || "").replaceAll("_", " ")}</p>
                      </div>
                      <span className="rounded-lg border border-amber-400/40 bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-300">
                        {Number(asset.institutionalScore || 0).toFixed(0)}
                      </span>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-stone-500">{asset.thesis}</p>
                    <p className="mt-2 rounded-md border border-stone-200 bg-black/10 px-2 py-1.5 text-[0.68rem] leading-4 text-stone-500">
                      {asset.reviewAction}
                    </p>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Gatilhos de revisao</p>
                <div className="mt-3 grid gap-2">
                  {(recommendationGovernance.extraordinaryReviewTriggers || []).slice(0, 5).map((item) => (
                    <p key={item} className="rounded-lg border border-stone-200 bg-black/10 px-3 py-2 text-xs leading-5 text-stone-500">{item}</p>
                  ))}
                </div>
              </div>
              {(recommendationGovernance.blockers || []).length ? (
                <div className="rounded-lg border border-amber-400/30 bg-amber-500/10 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-300">Pontos monitorados</p>
                  <div className="mt-2 space-y-1">
                    {recommendationGovernance.blockers.map((item) => (
                      <p key={item} className="text-xs leading-5 text-amber-100">{item}</p>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </section>
      ) : null}

      {confidenceReport.status ? (
        <section className="surface overflow-hidden">
          <div className="grid gap-4 border-b border-stone-200 p-4 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-amber-500" />
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">{confidenceReport.title}</p>
              </div>
              <p className="mt-2 text-3xl font-semibold text-stone-950">{Number(confidenceReport.overallScore || 0).toFixed(0)}/100</p>
              <p className="mt-1 text-sm font-semibold text-amber-300">{confidenceReport.classification}</p>
              <p className="mt-3 text-sm leading-6 text-stone-500">{confidenceReport.headline}</p>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {(confidenceReport.plainLanguage || []).map((item) => (
                <p key={item} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">
                  {item}
                </p>
              ))}
            </div>
          </div>
          <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-4">
            {(confidenceReport.gates || []).map((gate) => (
              <div key={gate.id} className={`rounded-lg border p-3 ${confidenceClass(gate.status)}`}>
                <div className="flex items-start justify-between gap-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em]">{gate.label}</p>
                  <span className="text-sm font-semibold">{Number(gate.score || 0).toFixed(0)}</span>
                </div>
                <p className="mt-2 text-xs leading-5">{gate.reading}</p>
              </div>
            ))}
          </div>
          <div className="border-t border-stone-200 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand">Regras que o Alpha nao negocia</p>
            <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-5">
              {(confidenceReport.nonNegotiables || []).map((item) => (
                <p key={item} className="rounded-lg border border-stone-200 bg-black/10 px-3 py-2 text-[0.7rem] leading-5 text-stone-500">
                  {item}
                </p>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {researchCenter ? (
        <section className="surface overflow-hidden">
          <div className="grid gap-4 border-b border-stone-200 p-4 xl:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)]">
            <div>
              <div className="flex items-center gap-2">
                <Newspaper size={18} className="text-amber-500" />
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Research & Evidence Center</p>
              </div>
              <h3 className="mt-2 text-xl font-semibold text-stone-950">Centro de evidencias da carteira</h3>
              <p className="mt-2 text-sm leading-6 text-stone-500">{researchCenter.headline}</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
                <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
                  <p className="text-stone-500">Ativos</p>
                  <p className="mt-1 text-lg font-semibold text-stone-950">{researchCenter.coverage?.assets || 0}</p>
                </div>
                <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
                  <p className="text-stone-500">Com evidencias</p>
                  <p className="mt-1 text-lg font-semibold text-stone-950">{researchCenter.coverage?.withEvidence || 0}</p>
                </div>
                <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
                  <p className="text-stone-500">Com noticias</p>
                  <p className="mt-1 text-lg font-semibold text-stone-950">{researchCenter.coverage?.withNews || 0}</p>
                </div>
                <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
                  <p className="text-stone-500">Noticias</p>
                  <p className="mt-1 text-lg font-semibold text-stone-950">{researchCenter.coverage?.newsItems || 0}</p>
                </div>
              </div>
            </div>
            <div className="grid gap-2 md:grid-cols-3">
              {(researchCenter.sourceHealth || []).map((source) => (
                <div key={source.area} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand">{source.area}</p>
                    <span className="text-sm font-semibold text-stone-950">{Number(source.confidenceScore || 0).toFixed(0)}%</span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-stone-500">{source.reading}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(22rem,0.85fr)]">
            <div className="grid gap-3 md:grid-cols-2">
              {researchReports.slice(0, 4).map((report) => (
                <div key={report.ticker} className="rounded-lg border border-stone-200 bg-black/10 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-stone-950">{report.ticker}</p>
                      <p className="text-xs text-stone-500">{report.name}</p>
                    </div>
                    <span className="rounded-lg border border-amber-400/40 bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-300">
                      {Number(report.researchScore || 0).toFixed(0)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-stone-500">{report.headline}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="rounded-md border border-stone-200 px-2 py-1 text-[0.65rem] uppercase tracking-[0.1em] text-stone-500">{report.status}</span>
                    <span className="rounded-md border border-stone-200 px-2 py-1 text-[0.65rem] uppercase tracking-[0.1em] text-stone-500">Confianca {report.confidence}</span>
                    <span className="rounded-md border border-stone-200 px-2 py-1 text-[0.65rem] uppercase tracking-[0.1em] text-stone-500">{report.evidence?.length || 0} evidencias</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-lg border border-stone-200 bg-stone-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Noticias monitoradas</p>
              <div className="mt-3 space-y-3">
                {researchNews.slice(0, 4).length ? (
                  researchNews.slice(0, 4).map((item) => (
                    <a key={item.id} href={item.url || undefined} target="_blank" rel="noreferrer" className="block rounded-lg border border-stone-200 bg-black/10 p-3 hover:border-amber-500/50">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-xs font-semibold text-amber-300">{item.ticker}</span>
                        <span className="text-[0.65rem] uppercase tracking-[0.1em] text-stone-500">{item.sentiment}</span>
                      </div>
                      <p className="mt-1 text-xs font-semibold leading-5 text-stone-950">{item.title}</p>
                      <p className="mt-1 text-[0.68rem] text-stone-500">{item.source}</p>
                    </a>
                  ))
                ) : (
                  <p className="rounded-lg border border-amber-400/30 bg-amber-500/10 p-3 text-xs leading-5 text-amber-200">
                    Nenhuma noticia recente foi carregada pelo backend agora. O centro de evidencias continua usando fundamentos, eventos e fatos internos.
                  </p>
                )}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 2xl:grid-cols-[minmax(0,1.45fr)_minmax(24rem,0.55fr)]">
        <div className="surface overflow-hidden">
          <div className="border-b border-stone-200 px-4 py-3">
            <div className="flex items-center gap-2">
              <BookOpenCheck size={18} className="text-amber-600" />
              <h3 className="font-semibold text-stone-950">Carteira Recomendada Alpha</h3>
            </div>
            <p className="mt-1 text-xs text-stone-500">Selecao principal para proventos, preservacao patrimonial e setores essenciais.</p>
            <p className="mt-2 text-xs font-semibold text-amber-600">
              Universo: {screener.rawUniverseCount || 0} tickers lidos, {screener.eligibleUniverseCount || 0} elegiveis, {screener.candidateCount || 0} candidatas fundamentalistas e {screener.selectedCount || 10} selecionadas.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1080px] table-fixed text-left text-sm">
              <colgroup>
                <col className="w-[8%]" />
                <col className="w-[10%]" />
                <col className="w-[7%]" />
                <col className="w-[13%]" />
                <col className="w-[12%]" />
                <col className="w-[28%]" />
                <col className="w-[22%]" />
              </colgroup>
              <thead className="bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                  {["Ativo", "Setor", "Peso", "Papel", "Leitura Alpha", "Tese", "Acompanhar"].map((head) => (
                    <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {sortedAssets.map((asset) => (
                  <tr key={asset.ticker} className="align-top hover:bg-stone-50">
                    <td className="px-4 py-3">
                      <p className="font-semibold text-stone-950">{asset.ticker}</p>
                      <p className="text-xs text-stone-500">{asset.name}</p>
                    </td>
                    <td className="px-4 py-3">{asset.sector}</td>
                    <td className="px-4 py-3 font-semibold text-amber-700">{pct(asset.targetWeight)}</td>
                    <td className="px-4 py-3">{asset.role}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-lg border border-amber-400/40 bg-amber-500/10 px-2.5 py-1.5 text-xs font-semibold text-amber-300">
                        {confidenceByTicker[asset.ticker]?.classification || alphaConviction(asset, validationByTicker[asset.ticker])}
                      </span>
                      {confidenceByTicker[asset.ticker] ? (
                        <p className="mt-2 text-[0.68rem] font-semibold text-stone-500">
                          Confianca {Number(confidenceByTicker[asset.ticker].score || 0).toFixed(0)}/100
                        </p>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-xs leading-5 text-stone-600">{alphaThesis(asset, validationByTicker[asset.ticker])}</p>
                    </td>
                    <td className="px-4 py-3">
                      <ul className="space-y-1 text-xs leading-5 text-stone-500">
                        {asset.watchpoints.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="surface p-4">
          <h3 className="font-semibold text-stone-950">Alocacao por setor</h3>
          <p className="text-xs text-stone-500">Peso-alvo da carteira recomendada.</p>
          <div className="mt-4" style={{ height: "19rem" }}>
            <ResponsiveContainer width="100%" height="100%">
              <RePieChart>
                <Pie data={data.dividendPortfolio.sectorAllocation} dataKey="value" nameKey="name" innerRadius={72} outerRadius={112} paddingAngle={3}>
                  {data.dividendPortfolio.sectorAllocation.map((entry, index) => (
                    <Cell key={entry.name} fill={palette[index % palette.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => pct(value)}
                  contentStyle={sectorTooltipStyle}
                  labelStyle={sectorTooltipLabelStyle}
                  wrapperStyle={{ outline: "none", pointerEvents: "none" }}
                />
                <Legend verticalAlign="bottom" height={44} wrapperStyle={{ fontSize: "0.75rem", paddingTop: "0.75rem" }} />
              </RePieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 space-y-2">
            {data.macroContext.points.map((point) => (
              <p key={point} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">{point}</p>
            ))}
          </div>
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <div className="flex items-center gap-2">
            <BookOpenCheck size={18} className="text-sky-500" />
            <h3 className="font-semibold text-stone-950">{fiiPortfolio.title || "Carteira Alpha FIIs - estudo inicial"}</h3>
          </div>
          <p className="mt-1 text-xs text-stone-500">{fiiPortfolio.profile}</p>
          {fiiPortfolio.taxNote ? <p className="mt-2 text-xs font-semibold text-amber-600">{fiiPortfolio.taxNote}</p> : null}
          {fiiPortfolio.validationNote ? (
            <p className="mt-2 rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold leading-5 text-amber-200">
              {fiiPortfolio.validationNote}
            </p>
          ) : null}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px] table-fixed text-left text-sm">
            <colgroup>
              <col className="w-[10%]" />
              <col className="w-[12%]" />
              <col className="w-[8%]" />
              <col className="w-[14%]" />
              <col className="w-[12%]" />
              <col className="w-[28%]" />
              <col className="w-[16%]" />
            </colgroup>
            <thead className="bg-stone-50 text-xs uppercase text-stone-500">
              <tr>
                {["FII", "Segmento", "Peso", "Papel", "Leitura Alpha", "Tese", "Acompanhar"].map((head) => (
                  <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {(fiiPortfolio.assets || []).map((asset) => (
                <tr key={asset.ticker} className="align-top hover:bg-stone-50">
                  <td className="px-4 py-3">
                    <p className="font-semibold text-stone-950">{asset.ticker}</p>
                    <p className="text-xs text-stone-500">{asset.name}</p>
                  </td>
                  <td className="px-4 py-3">{asset.segment}</td>
                  <td className="px-4 py-3 font-semibold text-amber-700">{pct(asset.targetWeight)}</td>
                  <td className="px-4 py-3">{asset.role}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-lg border border-sky-400/40 bg-sky-500/10 px-2.5 py-1.5 text-xs font-semibold text-sky-300">
                      {asset.alphaScore}/100
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-xs leading-5 text-stone-600">{asset.thesis}</p>
                  </td>
                  <td className="px-4 py-3">
                    <ul className="space-y-1 text-xs leading-5 text-stone-500">
                      {asset.watchpoints.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <div className="flex items-center gap-2">
            <Globe2 size={18} className="text-emerald-500" />
            <h3 className="font-semibold text-stone-950">{globalPortfolio.title || "Carteira Alpha Global - watchlist inicial"}</h3>
          </div>
          <p className="mt-1 text-xs text-stone-500">{globalPortfolio.profile}</p>
          {globalPortfolio.validationNote ? (
            <p className="mt-2 rounded-lg border border-emerald-400/25 bg-emerald-500/10 px-3 py-2 text-xs font-semibold leading-5 text-emerald-200">
              {globalPortfolio.validationNote}
            </p>
          ) : null}
          <div className="mt-3 grid gap-2 md:grid-cols-3">
            {(globalPortfolio.regionAllocation || []).map((item) => (
              <p key={item.name} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs font-semibold text-stone-600">
                {item.name}: {pct(item.value)}
              </p>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1180px] table-fixed text-left text-sm">
            <colgroup>
              <col className="w-[9%]" />
              <col className="w-[10%]" />
              <col className="w-[9%]" />
              <col className="w-[7%]" />
              <col className="w-[7%]" />
              <col className="w-[12%]" />
              <col className="w-[11%]" />
              <col className="w-[22%]" />
              <col className="w-[13%]" />
            </colgroup>
            <thead className="bg-stone-50 text-xs uppercase text-stone-500">
              <tr>
                {["Ativo", "Pais", "Regiao", "Moeda", "Peso", "Papel", "Score", "Tese", "Acompanhar"].map((head) => (
                  <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {(globalPortfolio.assets || []).map((asset) => (
                <tr key={asset.ticker} className="align-top hover:bg-stone-50">
                  <td className="px-4 py-3">
                    <p className="font-semibold text-stone-950">{asset.ticker}</p>
                    <p className="text-xs text-stone-500">{asset.name}</p>
                  </td>
                  <td className="px-4 py-3">{asset.country}</td>
                  <td className="px-4 py-3">{asset.region}</td>
                  <td className="px-4 py-3 font-semibold text-emerald-300">{asset.currency}</td>
                  <td className="px-4 py-3 font-semibold text-amber-700">{pct(asset.targetWeight)}</td>
                  <td className="px-4 py-3">{asset.role}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-lg border border-emerald-400/40 bg-emerald-500/10 px-2.5 py-1.5 text-xs font-semibold text-emerald-300">
                      {asset.alphaScore}/100
                    </span>
                    <p className="mt-2 text-[0.7rem] text-stone-500">{asset.conviction}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-xs leading-5 text-stone-600">{asset.thesis}</p>
                  </td>
                  <td className="px-4 py-3">
                    <ul className="space-y-1 text-xs leading-5 text-stone-500">
                      {(asset.watchpoints || []).map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-stone-200 px-4 py-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Globe2 size={18} className="text-emerald-500" />
                <h3 className="font-semibold text-stone-950">Backtest internacional com cambio</h3>
              </div>
              <p className="mt-1 text-xs text-stone-500">
                Compara stock direto, BDR proxy e ETF global em BRL, incluindo cambio e dividendos internacionais simulados.
              </p>
            </div>
            <div className="grid gap-2 md:grid-cols-[9rem_9rem_8rem_auto_auto]">
              <input
                className="field h-10"
                type="date"
                value={globalBacktestForm.start_date}
                onChange={(event) => setGlobalBacktestForm({ ...globalBacktestForm, start_date: event.target.value })}
              />
              <input
                className="field h-10"
                type="date"
                value={globalBacktestForm.end_date}
                onChange={(event) => setGlobalBacktestForm({ ...globalBacktestForm, end_date: event.target.value })}
              />
              <input
                className="field h-10"
                type="number"
                min="1"
                step="100"
                value={globalBacktestForm.initial_value}
                onChange={(event) => setGlobalBacktestForm({ ...globalBacktestForm, initial_value: event.target.value })}
                placeholder="Valor"
              />
              <button className="btn-primary h-10 px-4 text-sm" onClick={() => runGlobalBacktest(false)} disabled={globalBacktestLoading}>
                <LineChart size={16} />
                {globalBacktestLoading ? "Calculando" : "Calcular"}
              </button>
              <button className="btn-secondary h-10 px-3 text-sm" onClick={() => runGlobalBacktest(true)} disabled={globalBacktestLoading} title="Tentar atualizar com providers reais">
                <RefreshCw size={16} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-4">
          {globalBacktestError ? <ErrorState message={globalBacktestError} /> : null}
          <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {globalBacktestVehicles.map((vehicle) => (
              <div key={vehicle.id} className="min-h-[7rem] rounded-lg border border-stone-200 bg-stone-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">{vehicle.label}</p>
                <p className="mt-2 text-xl font-semibold text-stone-950">{currency.format(vehicle.finalValue || 0)}</p>
                <div className="mt-2 flex items-center justify-between gap-2 text-xs">
                  <span className={(vehicle.totalReturnPct || 0) >= 0 ? "font-semibold text-emerald-300" : "font-semibold text-rose-300"}>
                    {pct(vehicle.totalReturnPct)}
                  </span>
                  <span className="text-stone-500">Proventos: {currency.format(vehicle.dividendsBrl || 0)}</span>
                </div>
                <p className="mt-2 text-[0.68rem] leading-4 text-stone-500">{vehicle.description}</p>
              </div>
            ))}
            <div className="min-h-[7rem] rounded-lg border border-stone-200 bg-stone-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">Cambio USD/BRL</p>
              <p className="mt-2 text-xl font-semibold text-stone-950">
                {Number(activeGlobalBacktest.summary?.startUsdBrl || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                {" -> "}
                {Number(activeGlobalBacktest.summary?.endUsdBrl || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
              <p className="mt-2 text-xs text-stone-500">Impacto cambial estimado: {pct(activeGlobalBacktest.summary?.fxReturnPct)}</p>
            </div>
          </section>

          <div className="portfolio-backtest-note">
            <strong>Como ler:</strong> o estudo parte de {currency.format(activeGlobalBacktest.initialValueBrl || globalBacktestForm.initial_value || 1000)} e compara caminhos de exposicao internacional. Quando provider real nao entrega historico, o motor usa fallback identificado, sem fingir certeza.
          </div>

          <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="portfolio-backtest-chart p-3">
              <h4 className="font-semibold text-stone-950">Evolucao em reais</h4>
              <p className="text-xs text-stone-500">Stock direto, BDR proxy e ETF global no mesmo periodo.</p>
              <div className="mt-3 h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <ReLineChart data={globalBacktestRows} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                    <XAxis dataKey="month" tick={axisTick} />
                    <YAxis tickFormatter={(value) => currency.format(value)} tick={axisTick} width={76} />
                    <Tooltip formatter={(value) => currency.format(value)} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                    <Legend />
                    <Line type="monotone" dataKey="stockDirectValue" name="Stock direto" stroke="var(--primary)" strokeWidth={2.3} dot={false} />
                    <Line type="monotone" dataKey="bdrValue" name="BDR proxy" stroke="#74c7ff" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="globalEtfValue" name="ETF global" stroke="#3bd19f" strokeWidth={2} dot={false} />
                  </ReLineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="portfolio-backtest-chart p-3">
              <h4 className="font-semibold text-stone-950">Retorno final</h4>
              <p className="text-xs text-stone-500">Comparacao percentual dos tres caminhos.</p>
              <div className="mt-3 h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={globalBacktestVehicles} margin={{ top: 14, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                    <XAxis dataKey="label" tick={axisTick} />
                    <YAxis tickFormatter={(value) => `${value}%`} tick={axisTick} width={54} />
                    <Tooltip formatter={(value) => pct(value)} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                    <Bar dataKey="totalReturnPct" name="Retorno total" radius={[6, 6, 0, 0]}>
                      {globalBacktestVehicles.map((vehicle) => (
                        <Cell key={vehicle.id} fill={(vehicle.totalReturnPct || 0) >= 0 ? "#3bd19f" : "#f97373"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <div className="overflow-x-auto rounded-lg border border-stone-200">
            <table className="w-full min-w-[920px] text-left text-xs">
              <thead className="bg-stone-50 uppercase text-stone-500">
                <tr>
                  {["Criterio", "Stock direto", "BDR proxy", "ETF global"].map((head) => (
                    <th key={head} className="px-4 py-3 font-semibold">{head}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {(activeGlobalBacktest.comparison || []).map((row) => (
                  <tr key={row.criterion} className="align-top">
                    <td className="px-4 py-3 font-semibold text-stone-950">{row.criterion}</td>
                    <td className="px-4 py-3 text-stone-500">{row.stockDirect}</td>
                    <td className="px-4 py-3 text-stone-500">{row.bdrProxy}</td>
                    <td className="px-4 py-3 text-stone-500">{row.globalEtf}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {activeGlobalBacktest.warnings?.length ? (
            <div className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-200">
              {activeGlobalBacktest.warnings.slice(0, 3).map((warning) => <p key={warning}>{warning}</p>)}
            </div>
          ) : null}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="surface p-4">
          <div className="flex items-center gap-2">
            <LineChart size={18} className="text-emerald-500" />
            <h3 className="font-semibold text-stone-950">{data.backtest.title}</h3>
          </div>
          <p className="mt-1 text-xs text-stone-500">Periodo {data.backtest.period}. Historico nao garante repeticao futura.</p>
          <div className="mt-4 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <ReLineChart data={data.backtest.rows} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="month" tick={axisTick} />
                <YAxis tickFormatter={(value) => currency.format(value)} tick={axisTick} width={76} />
                <Tooltip formatter={(value) => currency.format(value)} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                <Legend />
                <Line type="monotone" dataKey="stockPortfolio" name="Carteira recomendada" stroke="var(--primary)" strokeWidth={2.2} dot={false} />
                <Line type="monotone" dataKey="fixedIncome" name="Renda fixa 1% a.m." stroke="#74c7ff" strokeWidth={2} dot={false} />
              </ReLineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-4">
          <div className="surface p-4">
            <div className="flex items-center gap-2">
              <Flame size={18} className="text-rose-400" />
              <h3 className="font-semibold text-stone-950">{data.spicePortfolio.title}</h3>
            </div>
            <p className="mt-2 text-sm leading-6 text-stone-500">{data.spicePortfolio.riskWarning}</p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {data.spicePortfolio.assets.map((asset) => (
                <div key={asset.ticker} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-stone-950">{asset.ticker}</p>
                      <p className="text-xs text-stone-500">{asset.name}</p>
                    </div>
                    <RiskBadge value={asset.riskLevel} />
                  </div>
                  <p className="mt-2 text-xs font-semibold uppercase tracking-[0.12em] text-brand">{asset.suggestedBand}</p>
                  <p className="mt-2 text-xs leading-5 text-stone-600">{asset.thesis}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="surface p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} className="text-rose-400" />
              <h3 className="font-semibold text-stone-950">{data.cryptoStudy.title}: {data.cryptoStudy.ticker}</h3>
            </div>
            <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-brand">
              Revisao {data.cryptoStudy.reviewFrequency} | {data.cryptoStudy.category} | Research {data.cryptoStudy.researchScore || data.cryptoStudy.selectionScore || 0}/100
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-4">
              <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Decisao Alpha</p>
                <p className="mt-1 text-sm font-semibold text-stone-950">{data.cryptoStudy.decisionLabel || "Oportunidade mensal"}</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Conviccao</p>
                <p className="mt-1 text-sm font-semibold text-stone-950">{data.cryptoStudy.conviction || cryptoReport.conviction || "Em pesquisa"}</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Preco</p>
                <p className="mt-1 text-sm font-semibold text-stone-950">{usd.format(data.cryptoStudy.priceUsd || 0)}</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-stone-500">Dados</p>
                <p className="mt-1 text-sm font-semibold text-stone-950">{data.cryptoStudy.dataMode === "live" ? "Varredura live" : "Fallback"}</p>
              </div>
            </div>
            {data.cryptoStudy.exchangeAccess ? (
              <p className="mt-2 rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold leading-5 text-amber-200">
                {data.cryptoStudy.exchangeAccess}
              </p>
            ) : null}
            <p className="mt-2 text-sm leading-6 text-stone-500">{data.cryptoStudy.thesis}</p>
            <p className="mt-3 rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-300">
              {data.cryptoStudy.allocationGuardrail}
            </p>
            {cryptoReport.finalVerdict ? (
              <div className="mt-3 rounded-lg border border-amber-400/30 bg-amber-500/10 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand">Research Alpha</p>
                <p className="mt-2 text-sm leading-6 text-stone-600">{cryptoReport.finalVerdict}</p>
                {cryptoReport.thesis ? <p className="mt-2 text-xs leading-5 text-stone-500">{cryptoReport.thesis}</p> : null}
              </div>
            ) : null}
            {cryptoReport.scoreBreakdown ? (
              <div className="mt-3 grid gap-2 sm:grid-cols-4">
                {Object.entries(cryptoReport.scoreBreakdown).map(([key, value]) => (
                  <div key={key} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                    <p className="text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-stone-500">{key}</p>
                    <p className="mt-1 text-sm font-semibold text-stone-950">{Number(value || 0).toFixed(1)}</p>
                  </div>
                ))}
              </div>
            ) : null}
            {cryptoReport.catalysts?.length ? (
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <div className="rounded-lg border border-emerald-400/20 bg-emerald-500/10 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-200">Catalisadores</p>
                  <div className="mt-2 space-y-1.5">
                    {cryptoReport.catalysts.map((item) => <p key={item} className="text-xs leading-5 text-emerald-100">{item}</p>)}
                  </div>
                </div>
                <div className="rounded-lg border border-rose-400/20 bg-rose-500/10 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-rose-200">Riscos</p>
                  <div className="mt-2 space-y-1.5">
                    {(cryptoReport.riskFactors || []).slice(0, 5).map((item) => <p key={item} className="text-xs leading-5 text-rose-100">{item}</p>)}
                  </div>
                </div>
              </div>
            ) : null}
            {cryptoReport.dueDiligence?.length ? (
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {cryptoReport.dueDiligence.map((item) => (
                  <div key={item.label} className="flex items-center justify-between gap-3 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2">
                    <p className="text-xs text-stone-600">{item.label}</p>
                    <span className={`rounded-md border px-2 py-1 text-[0.65rem] font-semibold uppercase ${item.status === "ok" ? "border-emerald-400/30 text-emerald-300" : "border-amber-400/30 text-amber-300"}`}>
                      {item.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
            {cryptoReport.scenarios?.length ? (
              <div className="mt-3 grid gap-2 md:grid-cols-3">
                {cryptoReport.scenarios.map((scenario) => (
                  <div key={scenario.name} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand">{scenario.name}</p>
                    <p className="mt-2 text-xs font-semibold text-stone-950">{scenario.studyMultiple}</p>
                    <p className="mt-2 text-xs leading-5 text-stone-500">{scenario.description}</p>
                  </div>
                ))}
              </div>
            ) : null}
            {data.cryptoStudy.whySelected?.length ? (
              <div className="mt-3 grid gap-2">
                {data.cryptoStudy.whySelected.map((item) => (
                  <p key={item} className="rounded-lg border border-emerald-400/20 bg-emerald-500/10 px-3 py-2 text-xs leading-5 text-emerald-200">{item}</p>
                ))}
              </div>
            ) : null}
            <div className="mt-3 grid gap-2">
              {data.cryptoStudy.monthlyScanCriteria.map((item) => (
                <p key={item} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">{item}</p>
              ))}
            </div>
            {data.cryptoStudy.watchpoints?.length ? (
              <div className="mt-3 grid gap-2">
                {data.cryptoStudy.watchpoints.map((item) => (
                  <p key={item} className="text-xs leading-5 text-stone-500">{item}</p>
                ))}
              </div>
            ) : null}
            <div className="mt-3 grid gap-2">
              {data.cryptoStudy.realityCheck.map((item) => (
                <p key={item} className="text-xs leading-5 text-stone-500">{item}</p>
              ))}
            </div>
            {data.cryptoStudy.ranking?.length ? (
              <div className="mt-4 rounded-lg border border-stone-200 bg-stone-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand">Top oportunidades do screener</p>
                <div className="mt-2 grid gap-2">
                  {data.cryptoStudy.ranking.slice(0, 5).map((candidate, index) => (
                    <div key={candidate.ticker} className="flex items-center justify-between gap-3 rounded-md border border-stone-200 bg-black/10 px-3 py-2">
                      <div>
                        <p className="text-sm font-semibold text-stone-950">#{index + 1} {candidate.ticker}</p>
                        <p className="text-[0.7rem] text-stone-500">{candidate.decisionType === "reforcar_tese_existente" ? "Ja esta na carteira" : "Nova oportunidade"} | {candidate.binancePairs?.join(", ")}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-amber-300">{candidate.alphaScore}/100</p>
                        <p className="text-[0.7rem] text-stone-500">{usd.format(candidate.priceUsd || 0)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="surface p-4">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-amber-500" />
          <h3 className="font-semibold text-stone-950">Como o Alpha deve evoluir esse modulo</h3>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-5">
          {data.methodology.map((item) => (
            <p key={item} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">{item}</p>
          ))}
        </div>
      </section>
    </div>
  );
}
