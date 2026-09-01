"""
Admin coupon management routes.

Requires admin authentication (admin@gmail.com / admin123).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin, AdminUser
from app.core.database import get_db
from app.models.discount import Coupon, DiscountType

router = APIRouter(prefix="/api/v1/admin/coupons", tags=["admin", "coupons"])


class CouponCreate(BaseModel):
    code: str
    description: str | None = None
    discount_type: DiscountType
    discount_value: Decimal
    min_order_amount: Decimal = Decimal("0")
    max_discount_amount: Decimal | None = None
    usage_limit: int | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class CouponUpdate(BaseModel):
    description: str | None = None
    discount_type: DiscountType | None = None
    discount_value: Decimal | None = None
    min_order_amount: Decimal | None = None
    max_discount_amount: Decimal | None = None
    usage_limit: int | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class CouponResponse(BaseModel):
    id: int
    code: str
    description: str | None
    discount_type: DiscountType
    discount_value: Decimal
    min_order_amount: Decimal
    max_discount_amount: Decimal | None
    usage_limit: int | None
    used_count: int
    is_active: bool
    starts_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CouponResponse])
def list_coupons(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """List all coupons (admin only)."""
    coupons = db.execute(select(Coupon).order_by(Coupon.created_at.desc())).scalars().all()
    return coupons


@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(
    payload: CouponCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Create a new coupon (admin only)."""
    existing = db.execute(select(Coupon).where(Coupon.code == payload.code.upper())).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Coupon code already exists")

    coupon = Coupon(
        code=payload.code.upper(),
        description=payload.description,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        min_order_amount=payload.min_order_amount,
        max_discount_amount=payload.max_discount_amount,
        usage_limit=payload.usage_limit,
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.put("/{coupon_id}", response_model=CouponResponse)
def update_coupon(
    coupon_id: int,
    payload: CouponUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Update an existing coupon (admin only)."""
    coupon = db.get(Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Coupon not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(coupon, field, value)

    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/{coupon_id}")
def delete_coupon(
    coupon_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Delete a coupon (admin only)."""
    coupon = db.get(Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Coupon not found")

    coupon.is_active = False
    db.commit()
    return {"status": "deactivated"}
