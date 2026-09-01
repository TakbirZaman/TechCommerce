from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.schemas.order import OrderResponse, OrderSummary
from app.services import order_service

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.get("", response_model=list[OrderSummary])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[OrderSummary]:
    orders = order_service.list_orders_for_customer(db, current_user.id)
    return [OrderSummary.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
def get_my_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderResponse:
    order = order_service.get_order_for_customer(db, current_user.id, order_id)
    return OrderResponse.model_validate(order)
