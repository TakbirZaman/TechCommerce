"""
Checkout service (Sections 6-10).

Flow:
  1. Load the user's cart.
  2. Re-fetch each product with a row lock (never trust cart-cached price/qty).
  3. Recompute subtotal / discount / delivery_charge / total server-side.
  4. Generate order number, create Order + OrderItem rows (price snapshot).
  5. Reserve stock for every item.
  6. Move order into PAYMENT_PENDING.
  7. Clear the cart.

Everything happens in one DB transaction: if reservation fails partway
through, the whole checkout rolls back and no order is left dangling.
"""
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import EmptyCartError, InsufficientStockError, ProductNotPurchasableError
from app.models.cart import Cart
from app.models.core_platform_stubs import Product
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.schemas.order import CheckoutRequest
from app.services import inventory_service
from app.services.order_state_machine import transition_order_status
from app.utils.order_number import generate_order_number

# Flat delivery charge for now — a real implementation would look this up
# from a shipping-zone table keyed by city/area. Kept explicit and isolated
# here so it's a one-line change once that table exists.
FLAT_DELIVERY_CHARGE = Decimal("60.00")


def _calculate_discount(subtotal: Decimal, discount_code: str | None) -> Decimal:
    """
    Placeholder discount calculation. No discount-code table exists yet in
    this branch, so any code is currently a no-op (returns 0). Wiring this
    to a real promotions table is out of scope for Branch 2 per the spec
    (Section 33 excludes advanced systems) but the seam is here.
    """
    return Decimal("0.00")


def checkout(db: Session, user_id: int, payload: CheckoutRequest) -> Order:
    cart = db.execute(select(Cart).where(Cart.user_id == user_id)).scalar_one_or_none()
    if cart is None or not cart.items:
        raise EmptyCartError("Cart is empty")

    order_items: list[OrderItem] = []
    reservations: list[tuple[int, int]] = []
    subtotal = Decimal("0.00")

    for cart_item in cart.items:
        product = db.execute(
            select(Product).where(Product.id == cart_item.product_id).with_for_update()
        ).scalar_one_or_none()

        if product is None or not product.is_active or not product.is_purchasable:
            raise ProductNotPurchasableError(
                f"Product {cart_item.product_id} is no longer available for purchase"
            )
        if cart_item.quantity > product.available_stock:
            raise InsufficientStockError(
                f"Only {product.available_stock} unit(s) of '{product.name}' available"
            )

        unit_price = product.price
        line_subtotal = unit_price * cart_item.quantity
        subtotal += line_subtotal

        order_items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=cart_item.quantity,
                unit_price=unit_price,
                subtotal=line_subtotal,
            )
        )
        reservations.append((product.id, cart_item.quantity))

    discount = _calculate_discount(subtotal, payload.discount_code)
    delivery_charge = FLAT_DELIVERY_CHARGE
    total_amount = subtotal - discount + delivery_charge

    order_number = generate_order_number(db, datetime.now(UTC).year)

    order = Order(
        order_number=order_number,
        user_id=user_id,
        subtotal=subtotal,
        discount=discount,
        delivery_charge=delivery_charge,
        total_amount=total_amount,
        payment_method=payload.payment_method,
        payment_status=PaymentStatus.UNPAID,
        order_status=OrderStatus.PENDING,
        shipping_full_name=payload.delivery.full_name,
        shipping_phone=payload.delivery.phone,
        shipping_address=payload.delivery.address,
        shipping_city=payload.delivery.city,
        shipping_area=payload.delivery.area,
        shipping_postal_code=payload.delivery.postal_code,
        items=order_items,
    )
    db.add(order)
    db.flush()  # assign order.id before reserving/logging

    # Reserve stock for every line item (Section 10). If any single
    # reservation fails, the exception propagates and the whole
    # transaction (order + prior reservations) rolls back.
    inventory_service.reserve_order_items(db, reservations)

    transition_order_status(db, order, OrderStatus.PAYMENT_PENDING)

    # Clear the cart now that it has been converted into an order.
    for item in list(cart.items):
        db.delete(item)

    db.commit()
    db.refresh(order)
    return order
