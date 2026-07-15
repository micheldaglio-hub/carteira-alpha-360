import {
  BarChart3,
  Bell,
  Bitcoin,
  BookOpenCheck,
  Brain,
  BriefcaseBusiness,
  ChevronDown,
  ChevronRight,
  Compass,
  Crown,
  Gauge,
  Home,
  LineChart,
  LogOut,
  Moon,
  Newspaper,
  PanelLeftClose,
  PanelLeftOpen,
  ReceiptText,
  Settings,
  ServerCog,
  ShieldAlert,
  Sparkles,
  Sun,
  Target,
} from "lucide-react";
import { useState } from "react";

const icons = {
  overview: Home,
  portfolio: BriefcaseBusiness,
  crypto: Bitcoin,
  analysis: Gauge,
  models: BookOpenCheck,
  premiumArea: Crown,
  premium: Newspaper,
  projections: LineChart,
  tax: ReceiptText,
  strategies: Compass,
  stress: ShieldAlert,
  copilot: Brain,
  ops: ServerCog,
  rebalance: Target,
  alerts: Bell,
  settings: Settings,
};

export const navigation = [
  { id: "overview", label: "Visao Geral" },
  { id: "portfolio", label: "Minha Carteira" },
  { id: "crypto", label: "Cripto" },
  { id: "analysis", label: "Analise da Carteira" },
  { id: "models", label: "Carteira Recomendada" },
  { id: "premiumArea", label: "Area Premium" },
  { id: "premium", label: "Research Premium", roles: ["admin", "editor", "reviewer"] },
  { id: "projections", label: "Projecoes" },
  { id: "tax", label: "Impostos" },
  { id: "strategies", label: "Estrategias" },
  { id: "stress", label: "Stress Test" },
  { id: "copilot", label: "Copilot" },
  { id: "ops", label: "Sistema" },
  { id: "rebalance", label: "Rebalanceamento" },
  { id: "alerts", label: "Alertas" },
  { id: "settings", label: "Configuracoes" },
];

export const navigationGroups = [
  { id: "patrimonio", label: "Patrimonio", items: ["overview", "portfolio", "crypto", "projections", "rebalance"] },
  { id: "inteligencia", label: "Inteligencia", items: ["analysis", "models", "premiumArea", "premium", "strategies", "stress", "copilot"] },
  { id: "gestao", label: "Gestao", items: ["tax", "alerts"] },
  { id: "sistema", label: "Sistema", items: ["ops", "settings"] },
];

const navigationById = Object.fromEntries(navigation.map((item) => [item.id, item]));

export function canAccessNavigationItem(item, user) {
  if (!item?.roles?.length) return true;
  const roles = new Set(user?.roles || []);
  return item.roles.some((role) => roles.has(role));
}

export function visibleNavigationItems(user) {
  return navigation.filter((item) => canAccessNavigationItem(item, user));
}

export default function Sidebar({
  active,
  collapsed,
  onChange,
  onLogout,
  onToggleCollapse,
  onToggleTheme,
  theme,
  user,
}) {
  const [openGroups, setOpenGroups] = useState({
    patrimonio: true,
    inteligencia: true,
    gestao: true,
    sistema: true,
  });
  const toggleGroup = (groupId) => setOpenGroups((current) => ({ ...current, [groupId]: !current[groupId] }));
  const visibleItems = visibleNavigationItems(user);
  const visibleItemIds = new Set(visibleItems.map((item) => item.id));

  const renderItem = (item) => {
    const Icon = icons[item.id];
    const selected = active === item.id;
    return (
      <button
        key={item.id}
        onClick={() => onChange(item.id)}
        className={`flex min-h-7 w-full items-center rounded-lg text-left text-[0.74rem] font-medium transition ${
          collapsed ? "justify-center px-0" : "gap-2.5 px-2.5"
        } ${
          selected
            ? "bg-[#1f5f45] text-black shadow-[0_10px_26px_rgba(245,200,75,0.16)]"
            : "text-stone-600 hover:bg-stone-100 hover:text-stone-950"
        }`}
        title={item.label}
      >
        <Icon size={15} />
        {!collapsed ? <span className="truncate">{item.label}</span> : <span className="sr-only">{item.label}</span>}
      </button>
    );
  };

  return (
    <aside
      className={`app-sidebar fixed inset-y-0 left-0 z-20 hidden border-r border-stone-200 bg-[#07080b] py-2 transition-[width,padding] duration-200 lg:flex lg:flex-col ${
        collapsed ? "w-[4.5rem] px-2.5" : "w-64 px-3"
      }`}
    >
      <div className={`flex items-center gap-3 ${collapsed ? "justify-center px-0" : "px-2"}`}>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#1f5f45] text-black shadow-[0_0_28px_rgba(245,200,75,0.2)]">
          <BarChart3 size={20} />
        </div>
        {!collapsed ? (
          <div className="min-w-0">
            <p className="truncate text-[0.95rem] font-semibold text-stone-950">Carteira Alpha 360</p>
            <p className="truncate text-[0.7rem] text-stone-500">Inteligencia patrimonial</p>
          </div>
        ) : null}
      </div>

      <button
        onClick={onToggleCollapse}
        className={`btn-secondary mt-2 h-8 text-xs ${collapsed ? "w-full px-0" : "w-full px-3"}`}
        title={collapsed ? "Expandir menu" : "Recolher menu"}
      >
        {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        {!collapsed ? <span>Recolher menu</span> : null}
      </button>

      <nav className="mt-2 flex flex-1 flex-col gap-1 overflow-hidden pb-2">
        {collapsed
          ? visibleItems.map((item) => renderItem(item))
          : navigationGroups.map((group) => {
              const groupItems = group.items.map((id) => navigationById[id]).filter((item) => visibleItemIds.has(item.id));
              if (groupItems.length === 0) return null;
              const isOpen = openGroups[group.id];
              return (
                <div key={group.id} className="min-h-0">
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.id)}
                    aria-label={isOpen ? "Recolher grupo de menu" : "Expandir grupo de menu"}
                    className="flex h-6 w-full items-center justify-between rounded-md px-2 text-[0.62rem] font-bold uppercase tracking-[0.14em] text-stone-500 hover:bg-stone-100 hover:text-stone-900"
                  >
                    <span aria-hidden="true">{group.label}</span>
                    {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                  </button>
                  {isOpen ? <div className="mt-1 grid gap-1">{groupItems.map((item) => renderItem(item))}</div> : null}
                </div>
              );
            })}
      </nav>

      <div className="rounded-lg border border-stone-200 bg-white p-2.5">
        {!collapsed ? (
          <>
            <div className="flex items-center gap-2 text-[0.78rem] font-semibold text-stone-900">
              <Sparkles size={15} className="text-amber-600" />
              <span className="truncate">{user?.fullName || "Investidor"}</span>
            </div>
            <p className="mt-1 truncate text-[0.68rem] text-stone-500">{user?.email}</p>
          </>
        ) : (
          <div className="flex items-center justify-center text-amber-600" title={user?.fullName || "Investidor"}>
            <Sparkles size={17} />
          </div>
        )}

        <div className={`mt-2 grid gap-2 ${collapsed ? "grid-cols-1" : "grid-cols-2"}`}>
          <button
            onClick={onToggleTheme}
            className="btn-secondary h-8 text-xs"
            title={theme === "dark" ? "Usar tema claro" : "Usar tema escuro"}
          >
            {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            {!collapsed ? <span>{theme === "dark" ? "Claro" : "Escuro"}</span> : null}
          </button>
          <button onClick={onLogout} className="btn-secondary h-8 text-xs" title="Sair">
            <LogOut size={15} />
            {!collapsed ? <span>Sair</span> : null}
          </button>
        </div>
      </div>
    </aside>
  );
}
