"""
Cart API routes (Section 4-5).

Guest cart - uses session_id from cookie.
No authentication required.
"""
from fastapi import APIRouter, Cookie, Depends, Request

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.cart import CartItemAddRequest, CartItemUpdateRequest, CartResponse
from app.services import cart_service

router = APIRouter(prefix="/api/v1/cart", tags=["cart"])


def get_session_id(request: Request) -> str:
    """Get session_id from cookie or generate new one."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        import secrets
        session_id = secrets.token_urlsafe(32)
    return session_id


@router.get("", response_model=CartResponse)
def get_cart(
    request: Request,
    db: Session = Depends(get_db),
):
    """Get current cart contents."""
    session_id = get_session_id(request)
    return cart_service.get_cart(db, session_id)


@router.post("/items", response_model=CartResponse)
def add_item(
    payload: CartItemAddRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Add an item to the cart."""
    session_id = get_session_id(request)
    return cart_service.add_item(db, session_id, payload.product_id, payload.quantity)


@router.put("/items/{item_id}", response_model=CartResponse)
def update_item(
    item_id: int,
    payload: CartItemUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update cart item quantity."""
    session_id = get_session_id(request)
    return cart_service.update_item_quantity(db, session_id, item_id, payload.quantity)


@router.delete("/items/{item_id}", response_model=CartResponse)
def remove_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Remove an item from the cart."""
    session_id = get_session_id(request)
    return cart_service.remove_item(db, session_id, item_id)


@router.delete("", response_model=CartResponse)
def clear_cart(
    request: Request,
    db: Session = Depends(get_db),
):
    """Clear all items from the cart."""
    session_id = get_session_id(request)
    return cart_service.clear_cart(db, session_id)
