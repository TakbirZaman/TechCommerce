"""
Verified-purchase determination (Section 14).

The frontend never supplies this — it is derived server-side from the
commerce module's order data at review-creation time.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.stubs import Order, OrderItem

# Order statuses that qualify as a "completed purchase" for review purposes.
# STUB NOTE: align this with feature/commerce's actual order status enum.
QUALIFYING_ORDER_STATUSES = {"delivered", "completed"}


def find_qualifying_order_id(db: Session, user_id: int, product_id: int) -> Optional[int]:
    """
    Returns the most recent qualifying order id for this user+product, or
    None. Used to populate Review.order_id server-side.
    """
    order = (
        db.query(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(
            Order.user_id == user_id,
            OrderItem.product_id == product_id,
            Order.status.in_(QUALIFYING_ORDER_STATUSES),
        )
        .order_by(Order.id.desc())
        .first()
    )
    return order.id if order else None
