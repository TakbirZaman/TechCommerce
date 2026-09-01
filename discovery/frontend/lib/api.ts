/**
 * Thin fetch wrapper for the discovery API.
 * STUB NOTE: replace API_BASE_URL with core-platform's shared API client
 * config / env var if one already exists, rather than duplicating it.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export async function apiGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`, typeof window === "undefined" ? "http://internal" : window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") return;
      if (Array.isArray(value)) {
        value.forEach((v) => url.searchParams.append(key, String(v)));
      } else {
        url.searchParams.set(key, String(value));
      }
    });
  }
  const res = await fetch(url.toString().replace("http://internal", ""));
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}
