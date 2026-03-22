const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Token management
// ---------------------------------------------------------------------------

export function getToken() {
  return localStorage.getItem("pokerlog_token");
}

export function setToken(token) {
  localStorage.setItem("pokerlog_token", token);
}

export function clearToken() {
  localStorage.removeItem("pokerlog_token");
}

export function isLoggedIn() {
  return !!getToken();
}

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

export async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed");
  }
  return response.json();
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchJsonAuth(path, options = {}) {
  const headers = { ...authHeaders(), ...options.headers };
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401) {
    clearToken();
    throw new Error("Session expired – please log in again.");
  }
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed");
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function postJson(path, body) {
  return fetchJsonAuth(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function putJson(path, body) {
  return fetchJsonAuth(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteJson(path) {
  return fetchJsonAuth(path, { method: "DELETE" });
}

export async function login(password) {
  const res = await fetch(`${API_BASE}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Login failed");
  }
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export function buildSeasonParam(seasons) {
  if (!seasons || seasons.length === 0) {
    return "";
  }
  const value = seasons.join(",");
  return `?seasons=${encodeURIComponent(value)}`;
}
