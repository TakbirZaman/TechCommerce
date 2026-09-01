"use client";

import { useSearchParams } from "next/navigation";
import { FilterPanel, type FilterDefinition } from "@/components/discovery/FilterPanel";
import { useComparisonStore } from "@/store/comparisonStore";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { parseFilters } from "@/lib/searchParams";
import type { ProductListItem, SearchResponse } from "@/hooks/useProductSearch";

export function CategoryBrowseClient({
  categorySlug,
  initialFilters,
  popularBrands,
}: {
  categorySlug: string;
  initialFilters: FilterDefinition[];
  popularBrands: { name: string; slug: string; product_count: number }[];
}) {
  const searchParams = useSearchParams();
  const filters = parseFilters(searchParams);
  const { add } = useComparisonStore();

  // Category browsing reuses the same /search endpoint with category-scoped
  // querying — sorting stays composable with filtering (Section 7).
  const { data, isLoading } = useQuery({
    queryKey: ["category-products", categorySlug, filters],
    queryFn: () =>
      apiGet<SearchResponse>("/search", {
        q: categorySlug,
        brand: filters.brand,
        status: filters.status,
        min_price: filters.min_price,
        max_price: filters.max_price,
        sort: filters.sort,
        page: filters.page,
        ...filters.spec,
      }),
  });

  return (
    <div className="mt-6 grid grid-cols-1 gap-8 md:grid-cols-[240px_1fr]">
      <aside>
        <h2 className="mb-3 text-sm font-semibold">Filters</h2>
        <FilterPanel filters={initialFilters} />
        {popularBrands.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-2 text-sm font-semibold">Popular Brands</h3>
            <ul className="space-y-1 text-sm">
              {popularBrands.map((b) => (
                <li key={b.slug}>
                  <a href={`/brands/${b.slug}`} className="hover:underline">
                    {b.name} ({b.product_count})
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>

      <section>
        {isLoading && <p role="status">Loading products…</p>}
        {data && (
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.results.map((product: ProductListItem) => (
              <li key={product.id} className="rounded-lg border border-border p-4">
                <a href={`/products/detail/${product.slug}`}>
                  <h3 className="text-sm font-medium">{product.name}</h3>
                  <p className="font-semibold">${product.price.toLocaleString()}</p>
                </a>
                <button
                  type="button"
                  className="mt-2 text-xs underline"
                  onClick={() => add(product.id, product.category.id)}
                >
                  Add to compare
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
