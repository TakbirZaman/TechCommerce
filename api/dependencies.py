"""
Data access dependencies for the API layer.

ProductRepository is the seam between this intelligence system and the
platform's existing product database (spec section 1: "Integrate with
[the existing systems]. Do not rewrite them."). InMemoryProductRepository
below is a placeholder implementation seeded with the same sample fixtures
used in tests, so the API is runnable and demonstrable without a live
Postgres connection. Swapping in a real repository means implementing
PostgresProductRepository with the same `get_by_category` /
`get_by_id` interface against the platform's actual `products` table —
no other code in api/ or ml/ needs to change.
"""

from __future__ import annotations

from typing import Protocol

from ml.data.schemas import Category, Product


class ProductRepository(Protocol):
    def get_by_category(self, category: Category) -> list[Product]: ...
    def get_by_id(self, product_id: str) -> Product | None: ...


class InMemoryProductRepository:
    """
    Placeholder repository. NOT the source of truth in a real deployment —
    replace with a repository backed by the platform's existing `products`
    table (spec section 2: the product database is the source of truth).
    """

    def __init__(self, products: list[Product]):
        self._products = products

    def get_by_category(self, category: Category) -> list[Product]:
        return [p for p in self._products if p.category == category]

    def get_by_id(self, product_id: str) -> Product | None:
        return next((p for p in self._products if p.product_id == product_id), None)


def get_product_repository() -> ProductRepository:
    """
    FastAPI dependency. Returns the in-memory placeholder catalog until a
    real PostgresProductRepository is wired in via this same function.
    """
    from ml.data.sample_products import SAMPLE_LAPTOPS  # demo data only — see class docstring

    return InMemoryProductRepository(SAMPLE_LAPTOPS)
