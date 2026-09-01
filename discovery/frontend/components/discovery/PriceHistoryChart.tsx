"use client";

import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { apiGet } from "@/lib/api";

interface PriceHistoryPoint {
  price: number;
  recorded_at: string;
  change_reason?: string;
}
interface PriceHistoryResponse {
  product_id: number;
  current_price: number;
  previous_price: number | null;
  lowest_price: number | null;
  highest_price: number | null;
  history: PriceHistoryPoint[];
}

/** Sections 18-19: price history summary + chart, real data only. */
export function PriceHistoryChart({ productId }: { productId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["price-history", productId],
    queryFn: () => apiGet<PriceHistoryResponse>(`/products/${productId}/price-history`),
  });

  if (isLoading) return <p role="status">Loading price history…</p>;
  if (!data) return null;

  const hasEnoughHistory = data.history.length >= 2;

  return (
    <section aria-label="Price history">
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <dt className="text-xs text-muted-foreground">Current Price</dt>
          <dd className="text-lg font-semibold">${data.current_price.toLocaleString()}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Previous Price</dt>
          <dd className="text-lg">{data.previous_price ? `$${data.previous_price.toLocaleString()}` : "—"}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Lowest Recorded</dt>
          <dd className="text-lg">{data.lowest_price ? `$${data.lowest_price.toLocaleString()}` : "—"}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Highest Recorded</dt>
          <dd className="text-lg">{data.highest_price ? `$${data.highest_price.toLocaleString()}` : "—"}</dd>
        </div>
      </dl>

      {hasEnoughHistory ? (
        <div className="mt-4 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.history}>
              <XAxis dataKey="recorded_at" tickFormatter={(v) => new Date(v).toLocaleDateString()} />
              <YAxis domain={["auto", "auto"]} />
              <Tooltip labelFormatter={(v) => new Date(v as string).toLocaleDateString()} formatter={(v) => [`$${v}`, "Price"]} />
              <Line type="stepAfter" dataKey="price" stroke="currentColor" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">Not enough price history yet for a chart.</p>
      )}
    </section>
  );
}
