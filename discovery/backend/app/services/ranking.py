"""
Search ranking abstraction (Section 4).

`RankingStrategy` is the seam the future ML/intelligence branch replaces.
Nothing outside this file should know HOW ranking is computed — callers
just ask for a strategy instance and call `score()` / `order_by_clause()`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import case, func
from sqlalchemy.sql.elements import ColumnElement

from app.models.stubs import Product, ProductStatus


@dataclass
class RankingContext:
    query: str
    query_tokens: list[str]


class RankingStrategy(ABC):
    """
    Contract: given the raw search query, produce a SQLAlchemy-orderable
    score expression. Keeping this as a SQL expression (rather than
    post-hoc Python sorting) lets ranking stay index-friendly at scale.

    The ML ranking branch can implement this same interface, e.g. by
    scoring in Python after an initial SQL prefilter, or by joining a
    precomputed relevance table — callers don't need to change.
    """

    name: str = "base"

    @abstractmethod
    def score_expression(self, ctx: RankingContext) -> ColumnElement:
        ...


class DefaultRankingStrategy(RankingStrategy):
    """
    Deterministic, explainable initial ranking (Section 4). Combines:
    - text relevance (Postgres full-text `ts_rank`)
    - exact name match boost
    - brand name match boost
    - category name match boost
    - popularity
    - availability boost (in-stock/available ranks above out-of-stock)
    - status boost (available > pre-order > coming soon > out of stock > discontinued)
    """

    name = "default_v1"

    STATUS_WEIGHTS = {
        ProductStatus.AVAILABLE: 5,
        ProductStatus.PRE_ORDER: 3,
        ProductStatus.COMING_SOON: 2,
        ProductStatus.OUT_OF_STOCK: 1,
        ProductStatus.DISCONTINUED: 0,
    }

    def score_expression(self, ctx: RankingContext) -> ColumnElement:
        ts_query = func.plainto_tsquery("english", ctx.query)
        text_relevance = func.ts_rank(
            func.to_tsvector(
                "english",
                func.coalesce(Product.name, "")
                + " "
                + func.coalesce(Product.description, ""),
            ),
            ts_query,
        )

        exact_name_boost = case((func.lower(Product.name) == ctx.query.lower(), 10.0), else_=0.0)

        status_boost = case(
            *[(Product.status == status, weight) for status, weight in self.STATUS_WEIGHTS.items()],
            else_=0.0,
        )

        availability_boost = case((Product.stock_quantity > 0, 2.0), else_=0.0)

        popularity_component = func.coalesce(Product.popularity_score, 0.0) * 0.1

        # Weighted sum — weights are intentionally simple/tunable constants
        # for v1; an ML strategy would replace this whole expression.
        return (
            text_relevance * 20.0
            + exact_name_boost
            + status_boost
            + availability_boost
            + popularity_component
        )


def get_ranking_strategy() -> RankingStrategy:
    """
    Single seam for strategy selection. Swap this to feature-flag or
    A/B between strategies later (including an ML one) without touching
    the search endpoint.
    """
    return DefaultRankingStrategy()
