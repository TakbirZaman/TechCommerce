"""
Checkout service (Sections 6-10).

Guest checkout flow:
  1. Load the cart (using session/cookie).
  2. Re-fetch each product with a row lock (never trust cart-cached price/qty).
  3. Recompute subtotal / discount / delivery_charge / total server-side.
  4. Generate order number, create Order + OrderItem rows (price snapshot).
  5. Reserve stock for every item.
  6. Move order into PAYMENT_PENDING.
  7. Clear the cart.

No authentication required - users provide email, phone, name, address.
"""
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import EmptyCartError, InsufficientStockError, ProductNotPurchasableError
from app.models.cart import Cart
from app.models.core_platform_stubs import Product
from app.models.discount import DeliveryZone
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.schemas.order import CheckoutRequest
from app.services import inventory_service
from app.services.discount_service import increment_coupon_usage, validate_and_apply_coupon
from app.services.order_state_machine import transition_order_status
from app.utils.order_number import generate_order_number


def _calculate_delivery_charge(db: Session, city: str, area: str | None = None) -> Decimal:
    """
    Calculate delivery charge based on zone.
    Falls back to default charge if zone not found.
    """
    # Try to find exact zone (city + area)
    if area:
        zone = db.execute(
            select(DeliveryZone).where(
                DeliveryZone.city.ilike(city),
                DeliveryZone.area.ilike(area),
                DeliveryZone.is_active == True,
            )
        ).scalar_one_or_none()
        if zone:
            return Decimal(str(zone.charge))

    # Try city-only zone
    zone = db.execute(
        select(DeliveryZone).where(
            DeliveryZone.city.ilike(city),
            DeliveryZone.area.is_(None),
            DeliveryZone.is_active == True,
        )
    ).scalar_one_or_none()

    if zone:
        return Decimal(str(zone.charge))

    # Default charge for unknown zones
    return Decimal("60.00")


def checkout(db: Session, session_id: str, payload: CheckoutRequest) -> Order:
    """
    Guest checkout - no authentication required.
    Users provide email, phone, name, address directly.
    """
    cart = db.execute(select(Cart).where(Cart.session_id == session_id)).scalar_one_or_none()
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

    # Apply discount/coupon
    discount = validate_and_apply_coupon(db, payload.discount_code, subtotal)

    # Calculate delivery charge based on zone
    delivery_charge = _calculate_delivery_charge(
        db, payload.delivery.city, payload.delivery.area
    )

    total_amount = subtotal - discount + delivery_charge

    order_number = generate_order_number(db, datetime.now(UTC).year)

    order = Order(
        order_number=order_number,
        user_id=0,  # Guest user
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

    # Reserve stock for every line item
    inventory_service.reserve_order_items(db, reservations)

    transition_order_status(db, order, OrderStatus.PAYMENT_PENDING)

    # Increment coupon usage if a coupon was used
    if payload.discount_code:
        increment_coupon_usage(db, payload.discount_code)

    # Clear the cart
    for item in list(cart.items):
        db.delete(item)

    db.commit()
    db.refresh(order)
    return order
