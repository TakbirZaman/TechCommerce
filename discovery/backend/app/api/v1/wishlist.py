"""
Wishlist endpoints (Section 25).

Simple wishlist - no auth required, uses session/cookie.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.stubs import Product, Wishlist
from app.schemas.product import ProductSummary

router = APIRouter(tags=["wishlist"])


class WishlistResponse(BaseModel):
    product_id: int
    product_name: str
    price: float
    image_url: str | None


@router.get("/wishlist")
def get_wishlist(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get user's wishlist products.
    Uses session ID from cookie for guest users.
    """
    # Get session ID from cookie or create new one
    session_id = request.cookies.get("session_id")
    if not session_id:
        return []

    # For simplicity, return empty list
    # In production, use session_id to fetch from Redis/database
    return []


@router.post("/wishlist/{product_id}")
def add_to_wishlist(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Add a product to wishlist (uses session)."""
    product = db.query(Product).filter(Product.id == product_id, Product.is_visible == True).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    # For simplicity, just return success
    # In production, store in Redis/database with session_id
    return {"status": "added", "product_id": product_id}


@router.delete("/wishlist/{product_id}")
def remove_from_wishlist(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Remove a product from wishlist."""
    return {"status": "removed", "product_id": product_id}


@router.get("/wishlist/check/{product_id}")
def check_wishlist(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Check if a product is in wishlist."""
    return {"in_wishlist": False}
