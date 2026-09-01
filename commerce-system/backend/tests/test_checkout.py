from decimal import Decimal

from app.core.exceptions import EmptyCartError, InsufficientStockError
from app.models.core_platform_stubs import Product
from app.models.order import OrderStatus
from app.schemas.order import CheckoutRequest, DeliveryInfo
from app.services import checkout_service


def _delivery_payload():
    return {
        "delivery": {
            "full_name": "Jane Doe",
            "phone": "01700000000",
            "address": "123 Road",
            "city": "Dhaka",
            "area": "Gulshan",
            "postal_code": "1212",
        },
        "payment_method": "BKASH",
    }


def test_checkout_empty_cart_raises(db_session, seed_user):
    payload = CheckoutRequest.model_validate(_delivery_payload())
    try:
        checkout_service.checkout(db_session, seed_user.id, payload)
        assert False, "expected EmptyCartError"
    except EmptyCartError:
        pass


def test_checkout_calculates_totals_and_reserves_stock(db_session, seed_user, seed_product):
    # add to cart via service layer directly to keep this test focused
    from app.services import cart_service

    cart_service.add_item(db_session, seed_user.id, seed_product.id, 3)

    payload = CheckoutRequest.model_validate(_delivery_payload())
    order = checkout_service.checkout(db_session, seed_user.id, payload)

    assert order.order_number.startswith("ORD-")
    assert order.subtotal == Decimal("300.00")
    assert order.delivery_charge == Decimal("60.00")
    assert order.total_amount == Decimal("360.00")
    assert order.order_status == OrderStatus.PAYMENT_PENDING
    assert len(order.items) == 1
    assert order.items[0].unit_price == Decimal("100.00")

    # stock reserved: total_stock unchanged, reserved_stock increased
    db_session.refresh(seed_product)
    assert seed_product.reserved_stock == 3
    assert seed_product.available_stock == 7


def test_checkout_clears_cart(db_session, seed_user, seed_product):
    from app.models.cart import Cart
    from app.services import cart_service

    cart_service.add_item(db_session, seed_user.id, seed_product.id, 2)
    payload = CheckoutRequest.model_validate(_delivery_payload())
    checkout_service.checkout(db_session, seed_user.id, payload)

    cart = db_session.query(Cart).filter(Cart.user_id == seed_user.id).one()
    assert cart.items == []


def test_checkout_insufficient_stock_raises(db_session, seed_user, seed_product):
    from app.services import cart_service

    # Add 5, then reduce available stock externally to simulate a race
    cart_service.add_item(db_session, seed_user.id, seed_product.id, 5)
    seed_product.total_stock = 2
    db_session.commit()

    payload = CheckoutRequest.model_validate(_delivery_payload())
    try:
        checkout_service.checkout(db_session, seed_user.id, payload)
        assert False, "expected InsufficientStockError"
    except InsufficientStockError:
        pass


def test_order_number_format_and_uniqueness(db_session, seed_user, seed_product):
    from app.services import cart_service

    numbers = set()
    for _ in range(3):
        cart_service.add_item(db_session, seed_user.id, seed_product.id, 1)
        payload = CheckoutRequest.model_validate(_delivery_payload())
        order = checkout_service.checkout(db_session, seed_user.id, payload)
        numbers.add(order.order_number)

    assert len(numbers) == 3
    for n in numbers:
        assert n.startswith("ORD-")
        assert len(n.split("-")[-1]) == 6
