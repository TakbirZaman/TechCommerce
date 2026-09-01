"""
Stage 5: hybrid recommendation with fallback (spec sections 18 & 29).

FinalScore = 0.40 * RequirementMatch (rule-based)
           + 0.20 * ContentSimilarity
           + 0.15 * BehavioralPreference   [0 if unavailable]
           + 0.10 * ProductQuality (rating)
           + 0.10 * Popularity (review_count, log-scaled)
           + 0.05 * PriceFit

Weights are configurable via HybridWeights, matching spec section 18's
explicit requirement. None of these weights are claimed to be tuned from
real data — they are the same illustrative starting point given in the
spec, to be replaced once real evaluation data (spec section 26) exists.

FALLBACK CHAIN (spec section 29): if the ML ranking model does not exist,
fails to load, or returns invalid output, this module silently omits the
ML component (renormalizing the remaining weights) rather than failing the
whole request — the user always gets a recommendation from rule-based +
content-based scoring at minimum.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ml.data.schemas import Product, UserRequirement
from ml.inference.content_based import content_similarity_score
from ml.inference.explain import generate_explanation
from ml.inference.rule_based import score_product


@dataclass(frozen=True)
class HybridWeights:
    requirement_match: float = 0.40
    content_similarity: float = 0.20
    behavioral: float = 0.15
    product_quality: float = 0.10
    popularity: float = 0.10
    price_fit: float = 0.05

    def as_dict(self) -> dict[str, float]:
        return {
            "requirement_match": self.requirement_match,
            "content_similarity": self.content_similarity,
            "behavioral": self.behavioral,
            "product_quality": self.product_quality,
            "popularity": self.popularity,
            "price_fit": self.price_fit,
        }


@dataclass
class HybridResult:
    product: Product
    final_score: float
    component_scores: dict[str, float]
    reasons: list[str]
    tradeoffs: list[str]
    engine: str  # "hybrid_v1" or "rule_based_v1" (fallback)


def _price_fit(product: Product, requirement: UserRequirement) -> float:
    if requirement.budget_max is None:
        return 1.0
    if product.price > requirement.budget_max:
        return 0.0
    # Closer to (but not over) budget_max scores slightly higher, rewarding
    # "gets you the most for your money" without penalizing cheaper options much.
    return 0.7 + 0.3 * (product.price / requirement.budget_max)


def _popularity(product: Product) -> float:
    # log-scaled so a handful of extra reviews doesn't dominate the score
    return min(1.0, math.log10(product.review_count + 1) / 3.0)  # ~1000 reviews -> 1.0


def score_hybrid(
    product: Product,
    requirement: UserRequirement,
    behavioral_score: float | None = None,
    ml_score: float | None = None,
    weights: HybridWeights = HybridWeights(),
) -> HybridResult:
    """
    Compute the hybrid score for one product.

    behavioral_score: [0,1] score from the user's interaction history, or
        None if unavailable (new user / cold start — spec section 17).
    ml_score: [0,1] score from a trained ranking model, or None if no model
        is registered/loaded, or the model failed (spec section 29
        fallback). When None, ML is simply excluded from the blend rather
        than defaulting to 0 (which would unfairly punish every product).
    """
    rule_candidate = score_product(product, requirement)
    content_score = content_similarity_score(product, requirement)
    quality_score = (product.rating / 5.0) if product.rating is not None else None
    popularity_score = _popularity(product)
    price_fit_score = _price_fit(product, requirement)

    components: dict[str, float | None] = {
        "requirement_match": rule_candidate.score,
        "content_similarity": content_score,
        "behavioral": behavioral_score,
        "product_quality": quality_score,
        "popularity": popularity_score,
        "price_fit": price_fit_score,
    }
    weight_map = weights.as_dict()
    if ml_score is not None:
        # ML ranking, when available, replaces content_similarity's slot in
        # the blend (configurable choice, kept simple and explicit here
        # rather than hidden) — pull content_similarity out of both the
        # weighting and the reported components.
        components.pop("content_similarity", None)
        components["ml_ranking"] = ml_score
        weight_map["ml_ranking"] = weight_map.pop("content_similarity")

    known_weight_total = sum(weight_map[k] for k in weight_map if components.get(k) is not None)
    engine = "hybrid_v1" if known_weight_total > 0 else "rule_based_v1"
    if known_weight_total <= 0:
        # Total fallback: nothing but rule-based is available.
        final_score = rule_candidate.score
    else:
        final_score = sum(
            weight_map[k] * components[k] for k in weight_map if components.get(k) is not None
        ) / known_weight_total

    reasons, tradeoffs = generate_explanation(rule_candidate, requirement)

    return HybridResult(
        product=product,
        final_score=round(min(1.0, max(0.0, final_score)), 4),
        component_scores={k: round(v, 4) for k, v in components.items() if v is not None},
        reasons=reasons,
        tradeoffs=tradeoffs,
        engine=engine,
    )


def rank_hybrid(
    products: list[Product],
    requirement: UserRequirement,
    behavioral_scores: dict[str, float] | None = None,
    ml_scores: dict[str, float] | None = None,
    weights: HybridWeights = HybridWeights(),
    top_n: int = 10,
) -> list[HybridResult]:
    behavioral_scores = behavioral_scores or {}
    ml_scores = ml_scores or {}
    results = [
        score_hybrid(
            p, requirement,
            behavioral_score=behavioral_scores.get(p.product_id),
            ml_score=ml_scores.get(p.product_id),
            weights=weights,
        )
        for p in products
    ]
    results.sort(key=lambda r: r.final_score, reverse=True)
    return results[:top_n]
