"""
Order retrieval + admin status update service (Sections 22-23, 31).

IDOR protection: get_order_for_customer() always filters by user_id in the
SAME query that fetches the order, so a customer can never retrieve
another user's order by guessing an ID — there is no separate
"fetch then check owner" step that could be forgotten.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidOrderStateTransitionError, OrderNotFoundError
from app.models.order import Order, OrderStatus
from app.services.order_state_machine import transition_order_status


def list_orders_for_customer(db: Session, user_id: int) -> list[Order]:
    return list(
        db.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        ).scalars()
    )


def get_order_for_customer(db: Session, user_id: int, order_id: int) -> Order:
    order = db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user_id)
    ).scalar_one_or_none()
    if order is None:
        raise OrderNotFoundError(f"Order {order_id} not found")
    return order


def list_orders_for_admin(db: Session, status: OrderStatus | None = None) -> list[Order]:
    stmt = select(Order).order_by(Order.created_at.desc())
    if status is not None:
        stmt = stmt.where(Order.order_status == status)
    return list(db.execute(stmt).scalars())


def get_order_for_admin(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise OrderNotFoundError(f"Order {order_id} not found")
    return order


# Statuses an admin is allowed to set directly via the admin endpoint.
# PAID is deliberately excluded — that transition may only happen through
# verified payment processing (payment_service.py), never by admin fiat,
# so an admin can't manually "mark paid" and bypass gateway verification.
ADMIN_SETTABLE_STATUSES = {
    OrderStatus.PROCESSING,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
    OrderStatus.CANCELLED,
    OrderStatus.REFUNDED,
}


def admin_update_order_status(db: Session, order_id: int, new_status: OrderStatus) -> Order:
    if new_status not in ADMIN_SETTABLE_STATUSES:
        raise InvalidOrderStateTransitionError(
            f"Admins cannot set order status to {new_status.value} directly"
        )
    order = get_order_for_admin(db, order_id)
    transition_order_status(db, order, new_status)
    db.commit()
    db.refresh(order)
    return order
