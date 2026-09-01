"""
Order status state machine (Section 9).

This module is the ONLY place allowed to mutate Order.order_status.
Every other service must call transition_order_status() rather than
assigning order.order_status directly, so illegal jumps (e.g.
DELIVERED -> PAYMENT_PENDING) are always rejected in one place.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidOrderStateTransitionError
from app.models.order import ALLOWED_ORDER_TRANSITIONS, Order, OrderStatus


def transition_order_status(db: Session, order: Order, new_status: OrderStatus) -> Order:
    if new_status == order.order_status:
        return order  # no-op transitions are allowed (idempotent callers)

    allowed = ALLOWED_ORDER_TRANSITIONS.get(order.order_status, set())
    if new_status not in allowed:
        raise InvalidOrderStateTransitionError(
            f"Cannot transition order {order.order_number} from "
            f"{order.order_status.value} to {new_status.value}"
        )

    order.order_status = new_status
    db.flush()
    return order
