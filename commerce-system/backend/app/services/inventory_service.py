"""
Inventory reservation service (Section 10).

Product.total_stock / Product.reserved_stock live on the core-platform
Product table (see app/models/core_platform_stubs.py). Commerce does not
own that table but does own the reservation LOGIC that mutates those two
columns, since reservation is a checkout-time concern.

Lifecycle:
  reserve_stock()   at order creation (PENDING -> PAYMENT_PENDING)
  release_stock()   on payment failure/cancellation/expiry
  finalize_stock()  on payment success — converts a reservation into a
                     permanent deduction (reserved_stock and total_stock
                     both decrease, so available_stock is unchanged but the
                     unit is no longer sitting in "reserved limbo")

All three use SELECT ... FOR UPDATE on the product row so concurrent
reservations against the same product serialize instead of racing.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientStockError, ProductNotFoundError
from app.models.core_platform_stubs import Product


def _lock_product(db: Session, product_id: int) -> Product:
    product = db.execute(
        select(Product).where(Product.id == product_id).with_for_update()
    ).scalar_one_or_none()
    if product is None:
        raise ProductNotFoundError(f"Product {product_id} not found")
    return product


def reserve_stock(db: Session, product_id: int, quantity: int) -> None:
    product = _lock_product(db, product_id)
    if quantity > product.available_stock:
        raise InsufficientStockError(
            f"Only {product.available_stock} unit(s) of '{product.name}' available"
        )
    product.reserved_stock += quantity
    db.flush()


def release_stock(db: Session, product_id: int, quantity: int) -> None:
    """Called on payment failure/cancellation/expiry to give reserved units back."""
    product = _lock_product(db, product_id)
    product.reserved_stock = max(product.reserved_stock - quantity, 0)
    db.flush()


def finalize_stock(db: Session, product_id: int, quantity: int) -> None:
    """
    Called on payment success. Converts a reservation into a permanent
    deduction: both total_stock and reserved_stock decrease by `quantity`,
    so available_stock (= total - reserved) is unaffected by this step —
    it was already reduced at reservation time.
    """
    product = _lock_product(db, product_id)
    product.total_stock = max(product.total_stock - quantity, 0)
    product.reserved_stock = max(product.reserved_stock - quantity, 0)
    db.flush()


def reserve_order_items(db: Session, items: list[tuple[int, int]]) -> None:
    """items: list of (product_id, quantity) tuples. Reserves all or raises on first failure."""
    for product_id, quantity in items:
        reserve_stock(db, product_id, quantity)


def release_order_items(db: Session, items: list[tuple[int, int]]) -> None:
    for product_id, quantity in items:
        release_stock(db, product_id, quantity)


def finalize_order_items(db: Session, items: list[tuple[int, int]]) -> None:
    for product_id, quantity in items:
        finalize_stock(db, product_id, quantity)
