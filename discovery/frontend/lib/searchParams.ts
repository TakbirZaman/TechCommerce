/**
 * URL-based filter state helpers (Section 8).
 *
 * Filters live in the URL (?brand=asus&ram_gb=16&max_price=100000) so
 * results are shareable, bookmarkable, back/forward-navigable, and
 * crawlable. Pages read filters via `parseFilters(searchParams)` (server
 * component friendly) and write them via `buildFilterUrl` (client-side
 * navigation on filter change).
 */
export type ParsedFilters = {
  brand?: string[];
  status?: string[];
  min_price?: number;
  max_price?: number;
  sort?: string;
  page?: number;
  spec: Record<string, string>;
};

const RESERVED_KEYS = new Set(["brand", "status", "min_price", "max_price", "sort", "page", "q"]);

export function parseFilters(searchParams: URLSearchParams): ParsedFilters {
  const spec: Record<string, string> = {};
  searchParams.forEach((value, key) => {
    if (!RESERVED_KEYS.has(key)) spec[key] = value;
  });

  return {
    brand: searchParams.getAll("brand").length ? searchParams.getAll("brand") : undefined,
    status: searchParams.getAll("status").length ? searchParams.getAll("status") : undefined,
    min_price: searchParams.get("min_price") ? Number(searchParams.get("min_price")) : undefined,
    max_price: searchParams.get("max_price") ? Number(searchParams.get("max_price")) : undefined,
    sort: searchParams.get("sort") ?? "relevance",
    page: searchParams.get("page") ? Number(searchParams.get("page")) : 1,
    spec,
  };
}

/** Returns a new query string with `updates` merged in (null/undefined removes a key). */
export function buildFilterUrl(current: URLSearchParams, updates: Record<string, string | string[] | number | null | undefined>): string {
  const next = new URLSearchParams(current.toString());
  Object.entries(updates).forEach(([key, value]) => {
    next.delete(key);
    if (value === null || value === undefined) return;
    if (Array.isArray(value)) {
      value.forEach((v) => next.append(key, v));
    } else {
      next.set(key, String(value));
    }
  });
  // Any filter change resets pagination.
  if (!("page" in updates)) next.delete("page");
  return `?${next.toString()}`;
}
