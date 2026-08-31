"""
Stage 2: content-based recommendation (spec section 12).

Represents the user's requirement as a vector (using the resolved feature
weights as the "ideal" profile — an explicit priority IS the requirement
vector's value on that dimension) and each product as its normalized
feature vector, then ranks by cosine similarity.

This is a different lens than rule_based.py's weighted sum: rule_based
scores "how good is this product, weighted by what matters to you" — a
product can score high just by being excellent everywhere. Cosine
similarity instead scores "how well does this product's shape match your
stated priorities' shape" — it rewards products that emphasize the same
dimensions the user emphasized, which behaves differently when, e.g., a
user wants a *balanced* laptop vs. one that maxes out a single dimension.

Missing specs are excluded from both vectors for a given comparison (not
treated as 0) — comparing only over commonly-known dimensions, consistent
with rule_based.py's handling of missing data (spec section 12).
"""

from __future__ import annotations

import math

from ml.data.schemas import Product, UserRequirement
from ml.features.feature_vectors import build_feature_vector
from ml.features.weights import resolve_weights


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    common_keys = [k for k in a if k in b]
    if not common_keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in common_keys)
    norm_a = math.sqrt(sum(a[k] ** 2 for k in common_keys))
    norm_b = math.sqrt(sum(b[k] ** 2 for k in common_keys))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def content_similarity_score(product: Product, requirement: UserRequirement) -> float:
    """
    Return a [0, 1] cosine-similarity score between the product's known
    feature vector and the requirement's weight profile.
    """
    requirement_vector = resolve_weights(requirement.category, requirement.use_cases, requirement.priorities)
    product_vector = build_feature_vector(product.category, product.raw_specs, product.price)
    known_product_vector = {k: v for k, v in product_vector.items() if v is not None}
    similarity = _cosine_similarity(requirement_vector, known_product_vector)
    return round(max(0.0, min(1.0, similarity)), 4)


def rank_by_content_similarity(
    products: list[Product], requirement: UserRequirement, top_n: int = 10
) -> list[tuple[Product, float]]:
    scored = [(p, content_similarity_score(p, requirement)) for p in products]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_n]
