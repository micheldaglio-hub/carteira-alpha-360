function resolveApiUrl() {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000/api";
  }
  return `${window.location.protocol}//${window.location.hostname}:8000/api`;
}

export const API_URL = resolveApiUrl();

export async function apiFetch(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Nao foi possivel conectar ao servidor. Verifique se o Carteira Alpha esta aberto e tente atualizar.");
  }
  if (!response.ok) {
    let message = "Nao foi possivel concluir a operacao.";
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
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Nao foi possivel conectar ao servidor. Verifique se o Carteira Alpha esta aberto e tente atualizar.");
  }
  if (!response.ok) {
    let message = "Nao foi possivel baixar o arquivo.";
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
