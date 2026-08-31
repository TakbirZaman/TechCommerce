"""
User interaction events (spec sections 13 & 14).

This module defines the event schema and a configurable weight table.
It does NOT implement storage — persistence belongs to the existing
platform's DB layer (a table this system writes to, not owns). In a real
deployment, InteractionEvent rows are written by the existing product/cart/
order services (or by an event-tracking middleware) and read here for
building user profiles and training data.

Weights are explicitly marked as starting values (spec section 14) — not
claimed to be optimal, and kept in one place so they're easy to tune based
on real click-through/conversion data later without touching scoring code.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    PRODUCT_VIEW = "PRODUCT_VIEW"
    SEARCH = "SEARCH"
    SEARCH_CLICK = "SEARCH_CLICK"
    COMPARE = "COMPARE"
    WISHLIST_ADD = "WISHLIST_ADD"
    CART_ADD = "CART_ADD"
    PURCHASE = "PURCHASE"
    REVIEW = "REVIEW"
    PRODUCT_CLICK = "PRODUCT_CLICK"


# Starting values only (spec section 14) — configurable, not assumed optimal.
# Kept as a plain dict (not hardcoded into scoring logic) so it can be
# overridden from config/DB without a code change.
DEFAULT_EVENT_WEIGHTS: dict[EventType, float] = {
    EventType.PRODUCT_VIEW: 1,
    EventType.SEARCH: 1,
    EventType.SEARCH_CLICK: 2,
    EventType.PRODUCT_CLICK: 2,
    EventType.COMPARE: 3,
    EventType.WISHLIST_ADD: 5,
    EventType.CART_ADD: 8,
    EventType.PURCHASE: 10,
    EventType.REVIEW: 6,
}


class InteractionEvent(BaseModel):
    user_id: str
    product_id: str
    event_type: EventType
    timestamp: datetime
    session_id: str | None = None
    context: dict = Field(default_factory=dict)  # e.g. {"source": "search", "query": "..."}

    model_config = {"extra": "forbid"}


def weighted_interaction_score(events: list[InteractionEvent], weights: dict[EventType, float] | None = None) -> float:
    """Sum of event weights for a set of events (e.g. all events for one user+product pair)."""
    active_weights = weights or DEFAULT_EVENT_WEIGHTS
    return sum(active_weights.get(e.event_type, 0) for e in events)
