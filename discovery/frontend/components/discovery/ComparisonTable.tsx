"use client";

import { useQuery } from "@tanstack/react-query";
import { apiPost } from "@/lib/api";
import { useComparisonStore } from "@/store/comparisonStore";

interface ComparisonRow {
  spec_key: string;
  spec_label: string;
  values: string[];
  differs: boolean;
}
interface ComparisonProductColumn {
  id: number;
  name: string;
  slug: string;
  price: number;
  status: string;
  brand: { name: string };
}
interface ComparisonResponse {
  category: { name: string; slug: string };
  products: ComparisonProductColumn[];
  rows: ComparisonRow[];
}

/** Sections 9-11: responsive comparison table with difference highlighting. */
export function ComparisonTable() {
  const { productIds, remove, clear } = useComparisonStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ["compare", productIds],
    queryFn: () => apiPost<ComparisonResponse>("/compare", { product_ids: productIds }),
    enabled: productIds.length >= 2,
  });

  if (productIds.length < 2) {
    return <p className="text-sm text-muted-foreground">Select at least 2 products of the same type to compare.</p>;
  }
  if (isLoading) return <p role="status">Loading comparison…</p>;
  if (error) return <p role="alert" className="text-sm text-destructive">Couldn&apos;t load comparison. Try again.</p>;
  if (!data) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm" aria-label={`Comparing ${data.category.name}`}>
        <caption className="sr-only">Product comparison table for {data.category.name}</caption>
        <thead>
          <tr>
            <th scope="col" className="p-2 text-left">Specification</th>
            {data.products.map((p) => (
              <th key={p.id} scope="col" className="p-2 text-left align-top">
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-muted-foreground">{p.brand.name}</div>
                <div className="font-semibold">${p.price.toLocaleString()}</div>
                <div className="text-xs">{p.status.replace("_", " ")}</div>
                <button
                  type="button"
                  className="mt-1 text-xs text-destructive underline"
                  onClick={() => remove(p.id)}
                >
                  Remove
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.spec_key} className={row.differs ? "bg-accent/40" : undefined}>
              <th scope="row" className="p-2 text-left font-normal">{row.spec_label}</th>
              {row.values.map((v, i) => (
                <td key={i} className="p-2">{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <button type="button" className="mt-4 text-sm underline" onClick={clear}>
        Clear comparison
      </button>
    </div>
  );
}
