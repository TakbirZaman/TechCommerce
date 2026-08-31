"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { ParsedFilters } from "@/lib/searchParams";

export interface ProductListItem {
  id: number;
  name: string;
  slug: string;
  sku: string;
  price: number;
  status: string;
  brand: { id: number; name: string; slug: string; logo_url?: string };
  category: { id: number; name: string; slug: string };
  thumbnail_url?: string;
  average_rating?: number;
  review_count: number;
  highlight_specs: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  page_size: number;
  results: ProductListItem[];
  applied_filters: Record<string, unknown>;
  ranking_strategy: string;
}

/** Search + filter + sort, composed into a single TanStack Query hook (Section 7). */
export function useProductSearch(query: string, filters: ParsedFilters) {
  return useQuery({
    queryKey: ["search", query, filters],
    queryFn: () =>
      apiGet<SearchResponse>("/search", {
        q: query,
        brand: filters.brand,
        status: filters.status,
        min_price: filters.min_price,
        max_price: filters.max_price,
        sort: filters.sort,
        page: filters.page,
        ...filters.spec,
      }),
    enabled: query.trim().length > 0,
    staleTime: 30_000,
  });
}

export interface AutocompleteSuggestion {
  label: string;
  type: "product" | "brand" | "category";
  slug?: string;
}

export function useAutocomplete(debouncedQuery: string) {
  return useQuery({
    queryKey: ["autocomplete", debouncedQuery],
    queryFn: () =>
      apiGet<{ query: string; suggestions: AutocompleteSuggestion[] }>("/search/autocomplete", {
        q: debouncedQuery,
      }),
    enabled: debouncedQuery.trim().length >= 2,
    staleTime: 60_000,
  });
}
