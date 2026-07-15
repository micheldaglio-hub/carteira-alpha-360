const API_PREFIX = "/api";

function configuredApiOrigin() {
  const env = import.meta.env || {};
  if (env.VITE_API_URL) {
    return env.VITE_API_URL;
  }
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000";
  }
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

export function resolveApiBaseUrl(baseUrl = configuredApiOrigin()) {
  const cleanBase = String(baseUrl || "").trim().replace(/\/+$/, "");
  if (!cleanBase) {
    return API_PREFIX;
  }
  return cleanBase.endsWith(API_PREFIX) ? cleanBase : `${cleanBase}${API_PREFIX}`;
}

export function normalizeApiPath(path = "") {
  const cleanPath = String(path || "").trim();
  if (!cleanPath) {
    return "";
  }
  const pathWithSlash = cleanPath.startsWith("/") ? cleanPath : `/${cleanPath}`;
  if (pathWithSlash === API_PREFIX) {
    return "";
  }
  if (pathWithSlash.startsWith(`${API_PREFIX}/`)) {
    return pathWithSlash.slice(API_PREFIX.length);
  }
  return pathWithSlash;
}

export function buildApiUrl(path, baseUrl = API_URL) {
  return `${resolveApiBaseUrl(baseUrl)}${normalizeApiPath(path)}`;
}

export const API_URL = resolveApiBaseUrl();

export async function apiFetch(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let response;
  try {
    response = await fetch(buildApiUrl(path), {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Não foi possível conectar ao servidor. Verifique se o Carteira Alpha está aberto e tente atualizar.");
  }
  if (!response.ok) {
    let message = "Não foi possível concluir a operação.";
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Keep fallback message.
    }
    throw new Error(message);
  }
  return response.json();
}

export async function apiDownload(path, { method = "GET", body, token, filename = "carteira-alpha-premium.pdf" } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  let response;
  try {
    response = await fetch(buildApiUrl(path), {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Não foi possível conectar ao servidor. Verifique se o Carteira Alpha está aberto e tente atualizar.");
  }
  if (!response.ok) {
    let message = "Não foi possível baixar o arquivo.";
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Keep fallback message.
    }
    throw new Error(message);
  }
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename=\"?([^\";]+)\"?/i);
  const resolvedFilename = match?.[1] || filename;
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = resolvedFilename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return { filename: resolvedFilename, size: blob.size };
}
