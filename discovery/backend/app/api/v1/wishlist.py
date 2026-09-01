"""
Wishlist endpoints (Section 25).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user_required, get_db
from app.models.stubs import Product, Wishlist
from app.schemas.product import ProductSummary

router = APIRouter(tags=["wishlist"])


@router.get("/wishlist", response_model=list[ProductSummary])
def get_wishlist(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_required),
):
    """Get user's wishlist products."""
    wishlist_items = db.query(Wishlist).filter(Wishlist.user_id == user.id).all()
    product_ids = [item.product_id for item in wishlist_items]
    products = db.query(Product).filter(Product.id.in_(product_ids), Product.is_visible == True).all()
    return products


@router.post("/wishlist/{product_id}", status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_required),
):
    """Add a product to user's wishlist."""
    product = db.query(Product).filter(Product.id == product_id, Product.is_visible == True).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    existing = db.query(Wishlist).filter(
        Wishlist.user_id == user.id, Wishlist.product_id == product_id
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Product already in wishlist")

    wishlist_item = Wishlist(user_id=user.id, product_id=product_id)
    db.add(wishlist_item)
    db.commit()
    return {"status": "added"}


@router.delete("/wishlist/{product_id}")
def remove_from_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_required),
):
    """Remove a product from user's wishlist."""
    wishlist_item = db.query(Wishlist).filter(
        Wishlist.user_id == user.id, Wishlist.product_id == product_id
    ).first()
    if not wishlist_item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not in wishlist")

    db.delete(wishlist_item)
    db.commit()
    return {"status": "removed"}


@router.get("/wishlist/check/{product_id}")
def check_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_required),
):
    """Check if a product is in user's wishlist."""
    exists = db.query(Wishlist).filter(
        Wishlist.user_id == user.id, Wishlist.product_id == product_id
    ).first() is not None
    return {"in_wishlist": exists}
