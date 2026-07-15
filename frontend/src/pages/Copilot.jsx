import { Brain, Database, RefreshCw, Send, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState } from "../components/EmptyState.jsx";
import { apiFetch } from "../lib/api.js";

function statusLabel(status) {
  if (status === "ai_enabled") return "IA conectada";
  return "Fallback interno";
}

function confidenceClass(confidence) {
  if (confidence === "alta") return "border-emerald-400/35 bg-emerald-500/10 text-emerald-200";
  if (confidence === "media") return "border-amber-400/35 bg-amber-500/10 text-amber-200";
  return "border-rose-400/35 bg-rose-500/10 text-rose-200";
}

function CitationCard({ citation }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-black/10 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Fonte interna</p>
          <h4 className="mt-1 text-sm font-semibold text-stone-950">{citation.title}</h4>
        </div>
        <span className={`rounded-lg border px-2 py-1 text-[0.68rem] font-semibold uppercase ${confidenceClass(citation.confidence)}`}>
          {citation.confidence}
        </span>
      </div>
      <p className="mt-2 text-xs leading-5 text-stone-500">{citation.excerpt}</p>
      <p className="mt-2 text-[0.68rem] uppercase tracking-[0.12em] text-stone-500">{citation.source}</p>
    </div>
  );
}

export default function Copilot({ token }) {
  const [status, setStatus] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      answer:
        "Bom, Michel. Eu sou o Alpha Copilot. Pergunte sobre sua carteira, risco, renda passiva, metas, estrategias ou stress test. Eu vou responder usando apenas dados internos e citar as fontes.",
      citations: [],
      warnings: [],
      followUps: [],
      confidence: "media",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    const [runtime, quick] = await Promise.all([
      apiFetch("/wealth-os/copilot/status", { token }),
      apiFetch("/wealth-os/copilot/questions", { token }),
    ]);
    setStatus(runtime);
    setQuestions(quick.questions || []);
  }

  useEffect(() => {
    let active = true;
    load().catch((err) => {
      if (active) setError(err.message);
    });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const latestCitations = useMemo(() => {
    const lastAssistant = [...messages].reverse().find((item) => item.role === "assistant" && item.citations?.length);
    return lastAssistant?.citations || [];
  }, [messages]);

  async function sendMessage(text = input) {
    const message = text.trim();
    if (!message || loading) return;
    setInput("");
    setError("");
    setMessages((current) => [...current, { role: "user", content: message }]);
    setLoading(true);
    try {
      const answer = await apiFetch("/wealth-os/copilot/chat", {
        method: "POST",
        token,
        body: { message },
      });
      setMessages((current) => [...current, { role: "assistant", ...answer }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (error && !status) return <ErrorState message={error} />;
  if (!status) return <LoadingState label="Carregando Alpha Copilot..." />;

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand">Alpha Copilot com IA</p>
          <h2 className="text-2xl font-semibold text-stone-950">Conversa patrimonial com fontes internas</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
            Pergunte em linguagem natural. O Copilot usa carteira, metas, Guardian, Strategy Engine, Stress Test,
            macro e confianca dos dados. Cada conclusao precisa apontar a origem.
          </p>
        </div>
        <div className="surface w-full p-3 xl:w-[26rem]">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Brain size={18} className="text-amber-500" />
              <div>
                <p className="text-sm font-semibold text-stone-950">{statusLabel(status.status)}</p>
                <p className="text-xs text-stone-500">{status.aiEnabled ? status.model : "Sem provider externo configurado"}</p>
              </div>
            </div>
            <button type="button" className="icon-button" title="Atualizar Copilot" onClick={load}>
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
      </header>

      {error ? <ErrorState message={error} /> : null}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="surface flex min-h-[34rem] flex-col overflow-hidden">
          <div className="border-b border-stone-200 p-4">
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-amber-500" />
              <h3 className="font-semibold text-stone-950">Chat do Alpha</h3>
            </div>
            <p className="mt-1 text-xs text-stone-500">A IA não acessa provider de mercado pelo frontend e não usa dados fora do contexto interno.</p>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((message, index) => {
              const assistant = message.role === "assistant";
              return (
                <div key={`${message.role}-${index}`} className={`flex ${assistant ? "justify-start" : "justify-end"}`}>
                  <div className={`max-w-[86%] rounded-lg border px-4 py-3 ${assistant ? "border-stone-200 bg-black/10" : "border-amber-400/40 bg-amber-500/15"}`}>
                    <p className="whitespace-pre-wrap text-sm leading-6 text-stone-950">{assistant ? message.answer : message.content}</p>
                    {assistant && message.citations?.length ? (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {message.citations.map((citation) => (
                          <span key={citation.id} className="rounded-md border border-amber-400/35 bg-amber-500/10 px-2 py-1 text-[0.68rem] font-semibold text-amber-200">
                            {citation.title}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {assistant && message.warnings?.length ? (
                      <div className="mt-3 space-y-1">
                        {message.warnings.map((warning) => (
                          <p key={warning} className="text-xs leading-5 text-stone-500">{warning}</p>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })}
            {loading ? (
              <div className="rounded-lg border border-stone-200 bg-black/10 px-4 py-3 text-sm text-stone-500">
                Consultando contexto interno...
              </div>
            ) : null}
          </div>

          <div className="border-t border-stone-200 p-4">
            <div className="mb-3 flex flex-wrap gap-2">
              {questions.slice(0, 5).map((question) => (
                <button
                  key={question.id}
                  type="button"
                  onClick={() => sendMessage(question.question)}
                  className="rounded-lg border border-stone-200 bg-black/10 px-3 py-2 text-xs font-semibold text-stone-600 transition hover:border-amber-400/45 hover:text-stone-950"
                >
                  {question.question}
                </button>
              ))}
            </div>
            <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_auto]">
              <textarea
                className="field min-h-[4.5rem] resize-none p-3 text-sm"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Pergunte: meu risco aumentou? por que meu score caiu? quanto falta para renda passiva?"
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                  }
                }}
              />
              <button type="button" className="btn-primary h-full min-h-[4.5rem] px-5" onClick={() => sendMessage()} disabled={loading || !input.trim()}>
                <Send size={17} />
                Enviar
              </button>
            </div>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="surface p-4">
            <div className="flex items-center gap-2">
              <ShieldCheck size={18} className="text-emerald-500" />
              <h3 className="font-semibold text-stone-950">Regras de segurança</h3>
            </div>
            <div className="mt-3 space-y-2">
              {(status.rules || []).map((rule) => (
                <p key={rule} className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">{rule}</p>
              ))}
            </div>
          </div>

          <div className="surface p-4">
            <div className="flex items-center gap-2">
              <Database size={18} className="text-amber-500" />
              <h3 className="font-semibold text-stone-950">Fontes da ultima resposta</h3>
            </div>
            <div className="mt-3 space-y-2">
              {latestCitations.length ? (
                latestCitations.map((citation) => <CitationCard key={citation.id} citation={citation} />)
              ) : (
                <p className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-600">
                  As fontes aparecem aqui depois da primeira resposta com dados internos.
                </p>
              )}
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
