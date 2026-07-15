import {
  BarChart3,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Moon,
  ShieldCheck,
  Sun,
  User,
  UserPlus,
} from "lucide-react";
import { useState } from "react";

const BACKGROUND_WEBP = "/assets/alpha-login-background.webp";
const BACKGROUND_PNG = "/assets/alpha-login-background.png";

const institutionalMetrics = [
  { value: "32", label: "Teses versionadas" },
  { value: "493", label: "Evidencias rastreaveis" },
  { value: "74/100", label: "Confianca dos dados" },
];

function BackgroundOverlay() {
  return (
    <>
      <picture className="auth-bg-picture" aria-hidden="true">
        <source srcSet={BACKGROUND_WEBP} type="image/webp" />
        <img className="auth-bg-image" src={BACKGROUND_PNG} alt="" decoding="async" fetchPriority="high" />
      </picture>
      <div className="auth-overlay auth-overlay-dark" aria-hidden="true" />
      <div className="auth-overlay auth-overlay-left" aria-hidden="true" />
      <div className="auth-overlay auth-overlay-vignette" aria-hidden="true" />
    </>
  );
}

function BrandMark({ compact = false }) {
  return (
    <div className={`flex items-center gap-3 ${compact ? "" : "auth-brand-mark"}`}>
      <div
        className={`flex items-center justify-center rounded-xl border border-[rgba(var(--primary-rgb),0.42)] bg-[var(--primary)] text-[#090806] shadow-[0_0_34px_rgba(var(--primary-rgb),0.28)] ${
          compact ? "h-11 w-11" : "h-14 w-14"
        }`}
      >
        <BarChart3 size={compact ? 23 : 29} strokeWidth={2.45} />
      </div>
      {!compact ? (
      <div>
        <p className={`${compact ? "text-[0.64rem]" : "text-[0.78rem]"} font-black uppercase tracking-[0.3em] text-[var(--primary)]`}>
          Carteira Alpha 360
        </p>
        <p className={`${compact ? "text-[0.64rem]" : "text-xs"} mt-1 font-bold uppercase tracking-[0.24em] text-white/76`}>
          Alpha Wealth OS
        </p>
        <p className="mt-1 text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-white/44">
          Institutional Wealth Intelligence
        </p>
      </div>
      ) : null}
    </div>
  );
}

function InstitutionalMetrics() {
  return (
    <div className="auth-metrics" aria-label="Indicadores demonstrativos institucionais">
      {institutionalMetrics.map((metric) => (
        <div className="auth-metric" key={metric.label}>
          <p className="auth-metric-value">{metric.value}</p>
          <p className="auth-metric-label">{metric.label}</p>
        </div>
      ))}
    </div>
  );
}

function AuthHero() {
  return (
    <section className="auth-hero">
      <div className="auth-hero-brand">
        <BrandMark />
      </div>

      <p className="text-[0.7rem] font-black uppercase tracking-[0.28em] text-[var(--primary)]">Wealth intelligence</p>
      <h1 className="auth-headline mt-4 max-w-2xl font-black text-white">
        Construa patrimonio.
        <span>Tome decisoes melhores.</span>
      </h1>
      <p className="auth-hero-promise mt-4 max-w-2xl text-base font-semibold leading-7 text-white/84 sm:text-lg">
        Carteira, research, estrategias, governanca, rastreabilidade e inteligencia patrimonial em uma unica plataforma.
      </p>
      <p className="auth-hero-extra mt-4 max-w-xl text-sm leading-6 text-white/64">
        Dados estruturados, evidencias auditaveis e decisoes mais bem fundamentadas para o longo prazo.
      </p>

      <InstitutionalMetrics />

      <p className="auth-demo-note mt-5 max-w-lg text-xs font-semibold text-white/50">
        Imagem e metricas do fundo sao demonstrativas.
      </p>
    </section>
  );
}

function AuthTabs({ mode, onChange }) {
  const tabs = [
    ["login", "Login"],
    ["register", "Cadastro"],
  ];

  return (
    <div aria-label="Modo de acesso" className="grid grid-cols-2 rounded-xl border border-white/12 bg-black/42 p-1" role="tablist">
      {tabs.map(([id, label]) => {
        const active = mode === id;
        return (
          <button
            aria-selected={active}
            className={`h-11 rounded-lg text-sm font-black transition ${
              active
                ? "bg-[var(--primary)] text-[#090806] shadow-[0_12px_28px_rgba(var(--primary-rgb),0.28)]"
                : "text-white/58 hover:bg-white/6 hover:text-white"
            }`}
            key={id}
            onClick={() => onChange(id)}
            role="tab"
            type="button"
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

function StatusMessage({ error, success }) {
  if (!error && !success) return null;

  const isError = Boolean(error);
  return (
    <p
      aria-live="polite"
      className={`rounded-lg border px-3 py-2 text-sm font-semibold ${
        isError
          ? "border-[rgba(var(--danger-rgb),0.42)] bg-[rgba(var(--danger-rgb),0.16)] text-[var(--danger)]"
          : "border-[rgba(var(--success-rgb),0.34)] bg-[rgba(var(--success-rgb),0.14)] text-[var(--success)]"
      }`}
      id="auth-status-message"
      role={isError ? "alert" : "status"}
    >
      {error || success}
    </p>
  );
}

function PasswordField({ error, isRegister, password, setPassword, showPassword, setShowPassword }) {
  return (
    <div>
      <label className="text-sm font-bold text-white/82" htmlFor="login-password">
        Senha
      </label>
      <div className="relative mt-1.5">
        <LockKeyhole
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/42"
          size={18}
        />
        <input
          aria-describedby={error ? "auth-status-message" : undefined}
          aria-invalid={Boolean(error)}
          autoComplete={isRegister ? "new-password" : "current-password"}
          className="field auth-field h-12 text-sm"
          id="login-password"
          onChange={(event) => setPassword(event.target.value)}
          required
          style={{ paddingLeft: "2.65rem", paddingRight: "2.65rem" }}
          type={showPassword ? "text" : "password"}
          value={password}
        />
        <button
          aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
          className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-white/50 hover:bg-white/8 hover:text-[var(--primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--border-focus)]"
          onClick={() => setShowPassword((current) => !current)}
          type="button"
        >
          {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
        </button>
      </div>
    </div>
  );
}

function SecurityTrustBar() {
  return (
    <div className="flex items-center justify-center gap-2 rounded-lg border border-[rgba(var(--primary-rgb),0.22)] bg-[rgba(var(--primary-rgb),0.08)] px-3 py-2 text-center text-[0.72rem] font-bold text-white/72">
      <ShieldCheck size={15} className="shrink-0 text-[var(--primary)]" />
      Acesso protegido • Dados isolados por usuario • Auditoria e rastreabilidade
    </div>
  );
}

function LegalDisclaimer() {
  return (
    <p className="rounded-lg border border-white/10 bg-black/32 px-3 py-2 text-xs leading-5 text-white/54">
      Analises sao informativas, baseadas em dados disponiveis e nao constituem promessa de rentabilidade.
    </p>
  );
}

function AuthCard({
  email,
  error,
  fullName,
  isRegister,
  loading,
  mode,
  onForgotPassword,
  onModeChange,
  onSubmit,
  password,
  remember,
  setEmail,
  setFullName,
  setPassword,
  setRemember,
  setShowPassword,
  showPassword,
  success,
  theme,
  onToggleTheme,
}) {
  return (
    <section aria-labelledby="auth-card-title" className="auth-card">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <BrandMark compact />
          <div>
            <p className="text-[0.68rem] font-black uppercase tracking-[0.2em] text-[var(--primary)]">Acesso seguro</p>
            <p className="mt-1 text-xs font-semibold text-white/56">Ambiente protegido do investidor</p>
          </div>
        </div>
        <button
          aria-label={theme === "dark" ? "Usar tema claro" : "Usar tema escuro"}
          className="icon-button shrink-0 border-white/14 bg-black/36 text-white hover:text-[var(--primary)]"
          onClick={onToggleTheme}
          title={theme === "dark" ? "Usar tema claro" : "Usar tema escuro"}
          type="button"
        >
          {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
        </button>
      </div>

      <div className="mt-5">
        <p className="text-xs font-black uppercase tracking-[0.22em] text-[var(--primary)]">Acesso institucional</p>
        <h2 className="mt-2 text-2xl font-black text-white" id="auth-card-title">
          Acessar meu Wealth OS
        </h2>
      </div>

      <AuthTabs mode={mode} onChange={onModeChange} />

      <form className="mt-4 space-y-3.5" onSubmit={onSubmit}>
        {isRegister ? (
          <label className="block" htmlFor="login-full-name">
            <span className="text-sm font-bold text-white/82">Nome completo</span>
            <div className="relative mt-1.5">
              <User
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/42"
                size={18}
              />
              <input
                autoComplete="name"
                className="field auth-field h-12 text-sm"
                id="login-full-name"
                onChange={(event) => setFullName(event.target.value)}
                required={isRegister}
                style={{ paddingLeft: "2.65rem" }}
                value={fullName}
              />
            </div>
          </label>
        ) : null}

        <label className="block" htmlFor="login-email">
          <span className="text-sm font-bold text-white/82">Email</span>
          <div className="relative mt-1.5">
            <Mail
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/42"
              size={18}
            />
            <input
              aria-describedby={error ? "auth-status-message" : undefined}
              aria-invalid={Boolean(error)}
              autoComplete="email"
              className="field auth-field h-12 text-sm"
              id="login-email"
              inputMode="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              style={{ paddingLeft: "2.65rem" }}
              type="email"
              value={email}
            />
          </div>
        </label>

        <PasswordField
          error={error}
          isRegister={isRegister}
          password={password}
          setPassword={setPassword}
          setShowPassword={setShowPassword}
          showPassword={showPassword}
        />

        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <label className="inline-flex cursor-pointer items-center gap-2 font-semibold text-white/76">
            <input
              checked={remember}
              className="h-4 w-4 accent-[var(--primary)]"
              onChange={(event) => setRemember(event.target.checked)}
              type="checkbox"
            />
            Manter conectado
          </label>
          <button
            className="font-bold text-[var(--primary)] underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--border-focus)]"
            onClick={onForgotPassword}
            type="button"
          >
            Esqueci minha senha
          </button>
        </div>

        <StatusMessage error={error} success={success} />

        <button className="btn-primary auth-submit h-12 w-full px-4 text-sm" disabled={loading} type="submit">
          {loading ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#080809] border-t-transparent" />
          ) : isRegister ? (
            <UserPlus size={18} />
          ) : (
            <LockKeyhole size={18} />
          )}
          {loading ? "Validando acesso..." : isRegister ? "Criar acesso Alpha 360" : "Acessar meu Wealth OS"}
        </button>
      </form>

      <div className="mt-4 space-y-3">
        <SecurityTrustBar />
        <LegalDisclaimer />
      </div>
    </section>
  );
}

export default function Login({ onLogin, onRegister, onToggleTheme, theme }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("demo@carteiraalpha.com");
  const [fullName, setFullName] = useState("Investidor Alpha");
  const [password, setPassword] = useState("Carteira@123");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const isRegister = mode === "register";

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (isRegister) {
        await onRegister({ email, full_name: fullName, password });
        setSuccess("Conta criada com sucesso. Preparando seu acesso seguro.");
      } else {
        await onLogin({ email, password });
        setSuccess("Acesso validado. Abrindo seu centro patrimonial.");
      }
    } catch (err) {
      setError(err.message || "Nao foi possivel concluir o acesso agora.");
    } finally {
      setLoading(false);
    }
  }

  function changeMode(nextMode) {
    setMode(nextMode);
    setError("");
    setSuccess("");
  }

  function handleForgotPassword() {
    setError("");
    setSuccess("Recuperacao de senha preparada para a proxima etapa, sem alterar a seguranca atual.");
  }

  return (
    <main className="auth-landing" data-theme={theme}>
      <BackgroundOverlay />
      <div className="auth-content">
        <AuthHero />
        <AuthCard
          email={email}
          error={error}
          fullName={fullName}
          isRegister={isRegister}
          loading={loading}
          mode={mode}
          onForgotPassword={handleForgotPassword}
          onModeChange={changeMode}
          onSubmit={submit}
          onToggleTheme={onToggleTheme}
          password={password}
          remember={remember}
          setEmail={setEmail}
          setFullName={setFullName}
          setPassword={setPassword}
          setRemember={setRemember}
          setShowPassword={setShowPassword}
          showPassword={showPassword}
          success={success}
          theme={theme}
        />
      </div>
    </main>
  );
}
