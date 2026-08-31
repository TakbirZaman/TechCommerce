"""
Rating aggregation with caching (Section 16).

Aggregates are cached in Redis (`k_rating_agg`) and invalidated whenever
a review's status changes (e.g. a moderator approves/hides a review) —
see api/v1/reviews.py. This avoids a `GROUP BY` over all reviews for a
product on every product-detail/list request.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import cache_delete, cache_get_json, cache_set_json, k_rating_agg
from app.core.config import settings
from app.models.review import Review, ReviewStatus
from app.schemas.review import RatingAggregate


def _compute_aggregate(db: Session, product_id: int) -> RatingAggregate:
    rows = (
        db.query(Review.rating, func.count(Review.id))
        .filter(Review.product_id == product_id, Review.status == ReviewStatus.APPROVED)
        .group_by(Review.rating)
        .all()
    )
    distribution = {i: 0 for i in range(1, 6)}
    total = 0
    weighted_sum = 0
    for rating, count in rows:
        distribution[rating] = count
        total += count
        weighted_sum += rating * count

    average = round(weighted_sum / total, 2) if total else 0.0
    return RatingAggregate(
        product_id=product_id,
        average_rating=average,
        review_count=total,
        distribution=distribution,
    )


async def get_rating_aggregate(db: Session, product_id: int) -> RatingAggregate:
    cache_key = k_rating_agg(product_id)
    cached_value = await cache_get_json(cache_key)
    if cached_value is not None:
        return RatingAggregate(**cached_value)

    agg = _compute_aggregate(db, product_id)
    await cache_set_json(cache_key, agg.model_dump(), settings.CACHE_TTL_RATING_AGG)
    return agg


async def invalidate_rating_aggregate(product_id: int) -> None:
    await cache_delete(k_rating_agg(product_id))
