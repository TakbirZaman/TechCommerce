"""
Related / similar products abstraction (Section 20).

`RelatedProductsStrategy` is the seam the intelligence branch replaces
with a learned model. The rule-based implementation here is intentionally
simple and explainable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.stubs import Product


class RelatedProductsStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def get_related(self, db: Session, product: Product, limit: int = 8) -> list[Product]:
        ...


class RuleBasedRelatedProducts(RelatedProductsStrategy):
    """
    Signals (Section 20): same category, same brand, similar price band,
    overlapping specification keys/values. No ML/embeddings.
    """

    name = "rule_based_v1"
    PRICE_BAND_PCT = 0.25  # +/-25% of the source product's price

    def get_related(self, db: Session, product: Product, limit: int = 8) -> list[Product]:
        low = product.price * (1 - self.PRICE_BAND_PCT)
        high = product.price * (1 + self.PRICE_BAND_PCT)

        same_category = db.query(Product).filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.is_visible.is_(True),
        )

        # Score in Python: category match is a prerequisite (comparability,
        # see Section 10), then rank by brand match + price closeness +
        # spec overlap.
        candidates = same_category.all()

        def score(candidate: Product) -> float:
            s = 0.0
            if candidate.brand_id == product.brand_id:
                s += 3.0
            if low <= candidate.price <= high:
                s += 2.0
            # Specification overlap: count matching key/value pairs.
            src_specs = product.specifications or {}
            cand_specs = candidate.specifications or {}
            overlap = sum(
                1 for k, v in src_specs.items() if k in cand_specs and cand_specs[k] == v
            )
            s += min(overlap, 5) * 0.5
            return s

        ranked = sorted(candidates, key=score, reverse=True)
        return ranked[:limit]


def get_related_products_strategy() -> RelatedProductsStrategy:
    return RuleBasedRelatedProducts()
