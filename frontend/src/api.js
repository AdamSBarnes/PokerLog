const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed");
  }
  return response.json();
}

export function buildSeasonParam(seasons) {
  if (!seasons || seasons.length === 0) {
    return "";
  }
  const value = seasons.join(",");
  return `?seasons=${encodeURIComponent(value)}`;
}

