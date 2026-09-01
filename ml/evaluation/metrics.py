"""
Recommendation quality metrics (spec section 26).

Pure functions over (ranked_product_ids, relevant_product_ids) — no
dependency on any particular model, so the same functions evaluate the
rule-based engine, content-based engine, or a future ML ranker identically.

"Relevant" is left for the caller to define from real interaction data
(e.g. products the user later purchased, added to cart, or clicked) — this
module does not fabricate what counts as relevant, per spec section 34's
prohibition on presenting manufactured data as real evaluation.
"""

from __future__ import annotations

import math


def precision_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = ranked_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for pid in top_k if pid in relevant_ids)
    return hits / len(top_k)


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    top_k = ranked_ids[:k]
    hits = sum(1 for pid in top_k if pid in relevant_ids)
    return hits / len(relevant_ids)


def mean_reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    for i, pid in enumerate(ranked_ids, start=1):
        if pid in relevant_ids:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    top_k = ranked_ids[:k]
    dcg = sum(
        (1.0 / math.log2(i + 1)) for i, pid in enumerate(top_k, start=1) if pid in relevant_ids
    )
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def hit_rate_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    top_k = ranked_ids[:k]
    return 1.0 if any(pid in relevant_ids for pid in top_k) else 0.0


def evaluate_ranking(ranked_ids: list[str], relevant_ids: set[str], k: int = 10) -> dict[str, float]:
    """Convenience aggregator returning all metrics for one query's ranking."""
    return {
        f"precision_at_{k}": round(precision_at_k(ranked_ids, relevant_ids, k), 4),
        f"recall_at_{k}": round(recall_at_k(ranked_ids, relevant_ids, k), 4),
        "mrr": round(mean_reciprocal_rank(ranked_ids, relevant_ids), 4),
        f"ndcg_at_{k}": round(ndcg_at_k(ranked_ids, relevant_ids, k), 4),
        f"hit_rate_at_{k}": round(hit_rate_at_k(ranked_ids, relevant_ids, k), 4),
    }
