"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { SearchBar } from "@/components/discovery/SearchBar";
import { useProductSearch } from "@/hooks/useProductSearch";
import { parseFilters, buildFilterUrl } from "@/lib/searchParams";

const SORT_OPTIONS = [
  { value: "relevance", label: "Relevance" },
  { value: "price_asc", label: "Price: Low to High" },
  { value: "price_desc", label: "Price: High to Low" },
  { value: "newest", label: "Newest" },
  { value: "popularity", label: "Popularity" },
  { value: "rating", label: "Rating" },
  { value: "discount", label: "Discount" },
];

export function SearchResultsClient({ initialQuery }: { initialQuery: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const filters = parseFilters(searchParams);
  const { data, isLoading, error } = useProductSearch(initialQuery, filters);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <SearchBar initialQuery={initialQuery} />
        <label className="flex items-center gap-2 text-sm">
          Sort by
          <select
            value={filters.sort}
            onChange={(e) => router.push(buildFilterUrl(searchParams, { sort: e.target.value }))}
            className="rounded-md border border-input px-2 py-1"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
      </div>

      {isLoading && <p role="status">Searching…</p>}
      {error && <p role="alert" className="text-destructive">Something went wrong. Please try again.</p>}

      {data && (
        <>
          <p className="mb-4 text-sm text-muted-foreground">{data.total} results</p>
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {data.results.map((product) => (
              <li key={product.id} className="rounded-lg border border-border p-4">
                <a href={`/products/${product.slug}`} className="block">
                  <div className="aspect-square w-full rounded-md bg-muted" aria-hidden="true" />
                  <h2 className="mt-2 text-sm font-medium">{product.name}</h2>
                  <p className="text-xs text-muted-foreground">{product.brand.name}</p>
                  <p className="mt-1 font-semibold">${product.price.toLocaleString()}</p>
                  {product.average_rating ? (
                    <p className="text-xs text-muted-foreground">
                      {product.average_rating.toFixed(1)}★ ({product.review_count})
                    </p>
                  ) : null}
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
