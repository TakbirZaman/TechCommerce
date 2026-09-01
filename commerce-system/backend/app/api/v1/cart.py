from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.schemas.cart import CartItemCreateRequest, CartItemUpdateRequest, CartResponse
from app.services import cart_service

router = APIRouter(prefix="/api/v1/cart", tags=["cart"])


@router.get("", response_model=CartResponse)
def read_cart(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CartResponse:
    return cart_service.get_cart(db, current_user.id)


@router.post("/items", response_model=CartResponse, status_code=201)
def add_cart_item(
    payload: CartItemCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CartResponse:
    return cart_service.add_item(db, current_user.id, payload.product_id, payload.quantity)


@router.patch("/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    item_id: int,
    payload: CartItemUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CartResponse:
    return cart_service.update_item_quantity(db, current_user.id, item_id, payload.quantity)


@router.delete("/items/{item_id}", response_model=CartResponse)
def delete_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CartResponse:
    return cart_service.remove_item(db, current_user.id, item_id)


@router.delete("", response_model=CartResponse)
def delete_cart(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CartResponse:
    return cart_service.clear_cart(db, current_user.id)
