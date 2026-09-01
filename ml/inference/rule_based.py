"""
Stage 1: rule-based recommender (spec section 7).

Deterministic, fully inspectable scoring: for each candidate product, build
its normalized feature vector, resolve the weight profile for the user's
category/use-cases/priorities, and compute a weighted sum over the features
that are actually known for that product.

Missing features are excluded from the weighted sum (and their weight
redistributed proportionally across known features) rather than counted as
zero — a product missing a spec should not be punished as if that spec were
bad (spec section 12). If a product has no known features at all, it scores
0.0 and effectively sorts last.
"""

from __future__ import annotations

from dataclasses import dataclass

from ml.data.schemas import Product, UserRequirement
from ml.features.feature_vectors import build_feature_vector
from ml.features.weights import resolve_weights


@dataclass(frozen=True)
class ScoredCandidate:
    product: Product
    score: float
    feature_vector: dict[str, float | None]
    weights: dict[str, float]
    known_feature_weight_share: float  # fraction of total weight backed by known specs


def score_product(product: Product, requirement: UserRequirement) -> ScoredCandidate:
    vector = build_feature_vector(product.category, product.raw_specs, product.price)
    weights = resolve_weights(requirement.category, requirement.use_cases, requirement.priorities)

    known_weight_total = sum(w for k, w in weights.items() if vector.get(k) is not None)
    if known_weight_total <= 0:
        return ScoredCandidate(product=product, score=0.0, feature_vector=vector,
                                weights=weights, known_feature_weight_share=0.0)

    weighted_sum = sum(
        weights[k] * vector[k] for k in weights if vector.get(k) is not None
    )
    # Renormalize by known weight so a product missing minor specs isn't
    # penalized purely for missing data.
    score = weighted_sum / known_weight_total
    return ScoredCandidate(
        product=product,
        score=round(min(1.0, max(0.0, score)), 4),
        feature_vector=vector,
        weights=weights,
        known_feature_weight_share=round(known_weight_total, 4),
    )


def rank_candidates(products: list[Product], requirement: UserRequirement, top_n: int = 10) -> list[ScoredCandidate]:
    scored = [score_product(p, requirement) for p in products]
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:top_n]
