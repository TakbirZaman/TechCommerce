import pytest

from app.core.exceptions import InvalidOrderStateTransitionError
from app.models.order import Order, OrderStatus, PaymentMethod
from app.services.order_state_machine import transition_order_status


def _make_order(db_session, seed_user, status: OrderStatus) -> Order:
    from decimal import Decimal

    order = Order(
        order_number="ORD-2026-000001",
        user_id=seed_user.id,
        subtotal=Decimal("100.00"),
        discount=Decimal("0.00"),
        delivery_charge=Decimal("0.00"),
        total_amount=Decimal("100.00"),
        payment_method=PaymentMethod.BKASH,
        order_status=status,
        shipping_full_name="Jane",
        shipping_phone="017",
        shipping_address="addr",
        shipping_city="Dhaka",
        shipping_area="Gulshan",
    )
    db_session.add(order)
    db_session.commit()
    return order


def test_valid_transition_allowed(db_session, seed_user):
    order = _make_order(db_session, seed_user, OrderStatus.PAYMENT_PENDING)
    transition_order_status(db_session, order, OrderStatus.PAID)
    assert order.order_status == OrderStatus.PAID


def test_delivered_to_payment_pending_rejected(db_session, seed_user):
    order = _make_order(db_session, seed_user, OrderStatus.DELIVERED)
    with pytest.raises(InvalidOrderStateTransitionError):
        transition_order_status(db_session, order, OrderStatus.PAYMENT_PENDING)


def test_cancelled_is_terminal(db_session, seed_user):
    order = _make_order(db_session, seed_user, OrderStatus.CANCELLED)
    with pytest.raises(InvalidOrderStateTransitionError):
        transition_order_status(db_session, order, OrderStatus.PAID)


def test_same_status_transition_is_noop(db_session, seed_user):
    order = _make_order(db_session, seed_user, OrderStatus.PAID)
    result = transition_order_status(db_session, order, OrderStatus.PAID)
    assert result.order_status == OrderStatus.PAID


def test_pending_to_shipped_directly_rejected(db_session, seed_user):
    order = _make_order(db_session, seed_user, OrderStatus.PENDING)
    with pytest.raises(InvalidOrderStateTransitionError):
        transition_order_status(db_session, order, OrderStatus.SHIPPED)
