import { Menu, Moon, RefreshCcw, Sun } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import Sidebar, { navigation, visibleNavigationItems } from "./components/Sidebar.jsx";
import { ErrorState } from "./components/EmptyState.jsx";
import { apiFetch } from "./lib/api.js";
import Alerts from "./pages/Alerts.jsx";
import Copilot from "./pages/Copilot.jsx";
import Crypto from "./pages/Crypto.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import ModelPortfolios from "./pages/ModelPortfolios.jsx";
import Ops from "./pages/Ops.jsx";
import Portfolio from "./pages/Portfolio.jsx";
import PremiumResearch from "./pages/PremiumResearch.jsx";
import PremiumSubscriber from "./pages/PremiumSubscriber.jsx";
import Projections from "./pages/Projections.jsx";
import Radar from "./pages/Radar.jsx";
import Rebalance from "./pages/Rebalance.jsx";
import Settings from "./pages/Settings.jsx";
import Strategies from "./pages/Strategies.jsx";
import StressTest from "./pages/StressTest.jsx";
import Tax from "./pages/Tax.jsx";

const savedToken = localStorage.getItem("carteira-alpha-token");
const savedTheme = localStorage.getItem("carteira-alpha-theme") || "dark";
const savedSidebarCollapsed = localStorage.getItem("carteira-alpha-sidebar-collapsed") === "true";

export default function App() {
  const [token, setToken] = useState(savedToken);
  const [user, setUser] = useState(null);
  const [active, setActive] = useState("overview");
  const [booting, setBooting] = useState(Boolean(savedToken));
  const [bootError, setBootError] = useState("");
  const [theme, setTheme] = useState(savedTheme);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(savedSidebarCollapsed);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("carteira-alpha-theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("carteira-alpha-sidebar-collapsed", String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  useEffect(() => {
    if (!token) return;
    setBooting(true);
    apiFetch("/auth/me", { token })
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("carteira-alpha-token");
        setToken(null);
      })
      .finally(() => setBooting(false));
  }, [token]);

  async function login(payload) {
    const result = await apiFetch("/auth/login", { method: "POST", body: payload });
    localStorage.setItem("carteira-alpha-token", result.access_token);
    setToken(result.access_token);
    setUser(result.user);
    setBootError("");
  }

  async function register(payload) {
    const result = await apiFetch("/auth/register", { method: "POST", body: payload });
    localStorage.setItem("carteira-alpha-token", result.access_token);
    setToken(result.access_token);
    setUser(result.user);
    setBootError("");
  }

  function logout() {
    localStorage.removeItem("carteira-alpha-token");
    setToken(null);
    setUser(null);
    setActive("overview");
  }

  const visibleNavigation = useMemo(() => visibleNavigationItems(user), [user]);
  const activeLabel = useMemo(() => visibleNavigation.find((item) => item.id === active)?.label || "Carteira Alpha 360", [active, visibleNavigation]);
  const toggleTheme = () => setTheme((current) => (current === "dark" ? "light" : "dark"));

  useEffect(() => {
    if (!token || !user) return;
    if (!visibleNavigation.some((item) => item.id === active)) {
      setActive("overview");
    }
  }, [active, token, user, visibleNavigation]);

  if (!token) {
    return <Login onLogin={login} onRegister={register} theme={theme} onToggleTheme={toggleTheme} />;
  }

  const page = {
    overview: <Dashboard token={token} />,
    portfolio: <Portfolio token={token} />,
    crypto: <Crypto token={token} />,
    analysis: <Radar token={token} kind="radar" />,
    dividends: <Radar token={token} kind="dividends" />,
    tax: <Tax token={token} />,
    growth: <Radar token={token} kind="growth" />,
    radar: <Radar token={token} kind="radar" />,
    models: <ModelPortfolios token={token} />,
    premiumArea: <PremiumSubscriber token={token} />,
    premium: <PremiumResearch token={token} />,
    strategies: <Strategies token={token} />,
    stress: <StressTest token={token} />,
    copilot: <Copilot token={token} />,
    ops: <Ops token={token} />,
    projections: <Projections token={token} />,
    rebalance: <Rebalance token={token} />,
    alerts: <Alerts token={token} />,
    settings: <Settings token={token} />,
  }[active];

  return (
    <div className="app-shell min-h-screen bg-[#050507]">
      <Sidebar
        active={active}
        collapsed={sidebarCollapsed}
        onChange={setActive}
        onToggleCollapse={() => setSidebarCollapsed((current) => !current)}
        onToggleTheme={toggleTheme}
        theme={theme}
        user={user}
        onLogout={logout}
      />
      <div className={sidebarCollapsed ? "lg:pl-[4.5rem]" : "lg:pl-64"}>
        <header className="app-header sticky top-0 z-10 border-b border-stone-200 bg-[#07080b]/95 px-4 py-2 backdrop-blur sm:px-5 lg:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <button className="icon-button lg:hidden" title="Menu">
                <Menu size={18} />
              </button>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand">Carteira Alpha 360</p>
                <h1 className="text-lg font-semibold text-stone-950">{activeLabel}</h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <select className="field h-10 w-44 lg:hidden" value={active} onChange={(event) => setActive(event.target.value)}>
                {visibleNavigation.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
              <button className="icon-button" title={theme === "dark" ? "Usar tema claro" : "Usar tema escuro"} onClick={toggleTheme}>
                {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
              </button>
              <button className="icon-button" title="Recarregar página" onClick={() => window.location.reload()}>
                <RefreshCcw size={17} />
              </button>
            </div>
          </div>
        </header>

        <main className="px-4 py-3 sm:px-5 lg:px-6">
          {bootError ? <ErrorState message={bootError} /> : null}
          {booting ? (
            <div className="surface p-4 text-sm text-stone-500">Restaurando sessão...</div>
          ) : (
            page
          )}
        </main>
      </div>
    </div>
  );
}
