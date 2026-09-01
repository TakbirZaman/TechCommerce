"""
Cart service (Branch 2, Sections 4-5).

Key rules enforced here:
- Price is ALWAYS read from Product.price at call time. Never trust client price.
- Quantity can never exceed available_stock (total_stock - reserved_stock).
- Race conditions are handled with SELECT ... FOR UPDATE on the product row
  for the duration of the quantity check, so two concurrent requests can't
  both "see" the same stock and both succeed.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    CartItemNotFoundError,
    InsufficientStockError,
    InvalidQuantityError,
    ProductNotFoundError,
    ProductNotPurchasableError,
)
from app.models.cart import Cart, CartItem
from app.models.core_platform_stubs import Product
from app.schemas.cart import CartItemResponse, CartResponse


def _get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = db.execute(select(Cart).where(Cart.user_id == user_id)).scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.flush()  # get cart.id without committing
    return cart


def _lock_product_or_404(db: Session, product_id: int) -> Product:
    """
    SELECT ... FOR UPDATE: locks the product row so concurrent cart/checkout
    operations against the same product serialize instead of racing on the
    stock check. Released automatically at transaction commit/rollback.
    """
    product = db.execute(
        select(Product).where(Product.id == product_id).with_for_update()
    ).scalar_one_or_none()
    if product is None:
        raise ProductNotFoundError(f"Product {product_id} not found")
    return product


def _validate_purchasable(product: Product) -> None:
    if not product.is_active:
        raise ProductNotPurchasableError(f"Product '{product.name}' is not active")
    if not product.is_purchasable:
        raise ProductNotPurchasableError(f"Product '{product.name}' is not purchasable")


def _to_item_response(item: CartItem, product: Product) -> CartItemResponse:
    unit_price = product.price
    return CartItemResponse(
        id=item.id,
        product_id=product.id,
        product_name=product.name,
        product_image_url=None,  # TODO: wire to core-platform product image URL once available
        unit_price=unit_price,
        quantity=item.quantity,
        subtotal=unit_price * item.quantity,
        available_stock=product.available_stock,
    )


def get_cart(db: Session, user_id: int) -> CartResponse:
    cart = _get_or_create_cart(db, user_id)
    db.commit()

    item_responses: list[CartItemResponse] = []
    for item in cart.items:
        product = db.get(Product, item.product_id)
        if product is None:
            # Product was deleted upstream; skip rather than crash the cart view.
            continue
        item_responses.append(_to_item_response(item, product))

    subtotal = sum((i.subtotal for i in item_responses), Decimal("0"))
    total_items = sum(i.quantity for i in item_responses)
    return CartResponse(items=item_responses, subtotal=subtotal, total_items=total_items)


def add_item(db: Session, user_id: int, product_id: int, quantity: int) -> CartResponse:
    if quantity <= 0:
        raise InvalidQuantityError("Quantity must be greater than zero")

    cart = _get_or_create_cart(db, user_id)
    product = _lock_product_or_404(db, product_id)
    _validate_purchasable(product)

    existing = db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
    ).scalar_one_or_none()

    new_quantity = (existing.quantity if existing else 0) + quantity
    if new_quantity > product.available_stock:
        raise InsufficientStockError(
            f"Only {product.available_stock} unit(s) of '{product.name}' available"
        )

    if existing:
        existing.quantity = new_quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product_id, quantity=new_quantity))

    db.commit()
    return get_cart(db, user_id)


def update_item_quantity(db: Session, user_id: int, item_id: int, quantity: int) -> CartResponse:
    if quantity <= 0:
        raise InvalidQuantityError("Quantity must be greater than zero. Use DELETE to remove an item.")

    cart = _get_or_create_cart(db, user_id)
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    ).scalar_one_or_none()
    if item is None:
        raise CartItemNotFoundError(f"Cart item {item_id} not found")

    product = _lock_product_or_404(db, item.product_id)
    _validate_purchasable(product)

    if quantity > product.available_stock:
        raise InsufficientStockError(
            f"Only {product.available_stock} unit(s) of '{product.name}' available"
        )

    item.quantity = quantity
    db.commit()
    return get_cart(db, user_id)


def remove_item(db: Session, user_id: int, item_id: int) -> CartResponse:
    cart = _get_or_create_cart(db, user_id)
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    ).scalar_one_or_none()
    if item is None:
        raise CartItemNotFoundError(f"Cart item {item_id} not found")

    db.delete(item)
    db.commit()
    return get_cart(db, user_id)


def clear_cart(db: Session, user_id: int) -> CartResponse:
    cart = _get_or_create_cart(db, user_id)
    for item in list(cart.items):
        db.delete(item)
    db.commit()
    return get_cart(db, user_id)
