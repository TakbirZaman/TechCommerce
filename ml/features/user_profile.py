"""
Derived user preference profile (spec section 15).

Computed on demand from InteractionEvent history + the products those
events reference — nothing here is permanently stored beyond what the
event log and product catalog already hold, consistent with "do not
permanently store every calculated value if it can be derived efficiently"
(spec section 15).

Caching: this function is a pure function of (events, products) and is
intended to be wrapped with a short-TTL Redis cache keyed by user_id at the
API layer (see api/dependencies.py) — no caching is implemented in this
module itself, since that is an infrastructure concern, not a modeling one.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ml.data.events import DEFAULT_EVENT_WEIGHTS, EventType, InteractionEvent
from ml.data.schemas import Product


@dataclass
class UserProfile:
    user_id: str
    favorite_categories: list[str] = field(default_factory=list)
    favorite_brands: list[str] = field(default_factory=list)
    price_range: tuple[float, float] | None = None
    interaction_count: int = 0


def build_user_profile(
    user_id: str,
    events: list[InteractionEvent],
    products_by_id: dict[str, Product],
    weights: dict[EventType, float] | None = None,
) -> UserProfile:
    """
    Build a UserProfile from a user's interaction events. Only events for
    `user_id` are considered; events referencing an unknown product_id are
    ignored (their weight contributes nothing, since we have no product data
    to attribute it to — never guessed).
    """
    active_weights = weights or DEFAULT_EVENT_WEIGHTS
    user_events = [e for e in events if e.user_id == user_id]

    category_weight: Counter[str] = Counter()
    brand_weight: Counter[str] = Counter()
    prices: list[float] = []

    for event in user_events:
        product = products_by_id.get(event.product_id)
        if product is None:
            continue
        w = active_weights.get(event.event_type, 0)
        category_weight[product.category.value] += w
        brand_weight[product.brand] += w
        prices.append(product.price)

    price_range = (min(prices), max(prices)) if prices else None

    return UserProfile(
        user_id=user_id,
        favorite_categories=[c for c, _ in category_weight.most_common(5)],
        favorite_brands=[b for b, _ in brand_weight.most_common(5)],
        price_range=price_range,
        interaction_count=len(user_events),
    )
