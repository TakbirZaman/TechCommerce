"""
Stage 1 pipeline (spec section 2 architecture, rule-based only):

  UserRequirement + candidate Products
    -> filter_candidates (hard constraints)
    -> rank_candidates (weighted rule-based scoring)
    -> generate_explanation (reasons/trade-offs from real data)
    -> RecommendationResponse

This is intentionally the only entry point external callers (a future
FastAPI route, tests, a notebook) should use for Stage 1. Later stages
(content-based, behavioral, ML ranking, hybrid) will plug in as alternate
or additional scorers behind this same interface, with fallback to this
rule-based engine per spec section 29.
"""

from __future__ import annotations

from ml.data.schemas import Product, RecommendationResponse, ScoredProduct, UserRequirement
from ml.inference.explain import generate_explanation
from ml.inference.filters import filter_candidates
from ml.inference.rule_based import rank_candidates


def recommend(products: list[Product], requirement: UserRequirement, top_n: int = 10) -> RecommendationResponse:
    candidates = filter_candidates(products, requirement)
    ranked = rank_candidates(candidates, requirement, top_n=top_n)

    scored_products = []
    for candidate in ranked:
        reasons, tradeoffs = generate_explanation(candidate, requirement)
        scored_products.append(
            ScoredProduct(
                product_id=candidate.product.product_id,
                score=candidate.score,
                reasons=reasons,
                tradeoffs=tradeoffs,
                component_scores={k: v for k, v in candidate.feature_vector.items() if v is not None},
            )
        )

    return RecommendationResponse(
        requirement=requirement,
        recommendations=scored_products,
        candidates_considered=len(products),
        candidates_after_filtering=len(candidates),
        engine="rule_based_v1",
    )
