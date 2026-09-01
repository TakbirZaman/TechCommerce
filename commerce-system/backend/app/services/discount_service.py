"""
Discount/Coupon service (Section 33).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidCouponError
from app.models.discount import Coupon, DiscountType


def validate_and_apply_coupon(
    db: Session, coupon_code: str | None, subtotal: Decimal
) -> Decimal:
    """
    Validate a coupon code and calculate the discount amount.
    
    Args:
        db: Database session
        coupon_code: The coupon code to validate
        subtotal: Order subtotal before discount
        
    Returns:
        Discount amount (Decimal)
        
    Raises:
        InvalidCouponError: If coupon is invalid or expired
    """
    if not coupon_code or not coupon_code.strip():
        return Decimal("0.00")

    coupon_code = coupon_code.strip().upper()

    # Find the coupon
    stmt = select(Coupon).where(Coupon.code == coupon_code)
    coupon = db.execute(stmt).scalar_one_or_none()

    if coupon is None:
        raise InvalidCouponError("Invalid coupon code")

    # Check if coupon is active
    if not coupon.is_active:
        raise InvalidCouponError("This coupon is no longer active")

    # Check expiration
    now = datetime.now(UTC)
    if coupon.expires_at and coupon.expires_at < now:
        raise InvalidCouponError("This coupon has expired")

    # Check start date
    if coupon.starts_at and coupon.starts_at > now:
        raise InvalidCouponError("This coupon is not yet valid")

    # Check usage limit
    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        raise InvalidCouponError("This coupon has reached its usage limit")

    # Check minimum order amount
    if subtotal < coupon.min_order_amount:
        raise InvalidCouponError(
            f"Minimum order amount of ৳{coupon.min_order_amount} required"
        )

    # Calculate discount
    if coupon.discount_type == DiscountType.PERCENTAGE:
        discount = subtotal * (coupon.discount_value / Decimal("100"))
    else:  # FIXED
        discount = coupon.discount_value

    # Apply max discount limit if set
    if coupon.max_discount_amount and discount > coupon.max_discount_amount:
        discount = coupon.max_discount_amount

    # Ensure discount doesn't exceed subtotal
    if discount > subtotal:
        discount = subtotal

    return discount


def increment_coupon_usage(db: Session, coupon_code: str) -> None:
    """Increment the usage count for a coupon after successful order."""
    if not coupon_code:
        return

    stmt = select(Coupon).where(Coupon.code == coupon_code.strip().upper())
    coupon = db.execute(stmt).scalar_one_or_none()
    if coupon:
        coupon.used_count += 1
        db.commit()
