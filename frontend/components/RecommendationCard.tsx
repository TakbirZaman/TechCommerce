import type { ScoredProduct } from "@/lib/api";

interface RecommendationCardProps {
  product: ScoredProduct;
  onCompare?: (productId: string) => void;
  onAddToCart?: (productId: string) => void;
  onViewDetails?: (productId: string) => void;
}

export function RecommendationCard({
  product,
  onCompare,
  onAddToCart,
  onViewDetails,
}: RecommendationCardProps) {
  const matchPercent = Math.round(product.score * 100);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-500">
          Product #{product.product_id}
        </span>
        <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
          {matchPercent}% match
        </span>
      </div>

      {product.reasons.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Why this one
          </p>
          <ul className="mt-1 space-y-1 text-sm text-slate-700">
            {product.reasons.map((reason) => (
              <li key={reason} className="flex gap-2">
                <span className="text-emerald-600">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {product.tradeoffs.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Trade-offs
          </p>
          <ul className="mt-1 space-y-1 text-sm text-slate-500">
            {product.tradeoffs.map((tradeoff) => (
              <li key={tradeoff} className="flex gap-2">
                <span className="text-amber-500">•</span>
                <span>{tradeoff}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 flex gap-2 border-t border-slate-100 pt-3">
        <button
          onClick={() => onViewDetails?.(product.product_id)}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          View details
        </button>
        <button
          onClick={() => onCompare?.(product.product_id)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Compare
        </button>
        <button
          onClick={() => onAddToCart?.(product.product_id)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Add to cart
        </button>
      </div>
    </div>
  );
}
