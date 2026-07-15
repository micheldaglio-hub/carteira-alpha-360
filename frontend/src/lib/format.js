export const currency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

export const compactCurrency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
  maximumFractionDigits: 1,
});

export function money(value, code = "BRL") {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: code || "BRL",
  }).format(value || 0);
}

export function pct(value) {
  return `${Number(value || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;
}

export function scoreColor(score) {
  if (score >= 82) return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (score >= 68) return "text-amber-700 bg-amber-50 border-amber-200";
  if (score >= 52) return "text-sky-700 bg-sky-50 border-sky-200";
  if (score >= 38) return "text-amber-700 bg-amber-50 border-amber-200";
  return "text-rose-700 bg-rose-50 border-rose-200";
}
