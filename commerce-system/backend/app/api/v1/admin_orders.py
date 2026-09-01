from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, require_admin
from app.models.order import OrderStatus
from app.schemas.order import AdminOrderStatusUpdateRequest, OrderResponse, OrderSummary
from app.services import order_service

router = APIRouter(prefix="/api/v1/admin/orders", tags=["admin-orders"])


@router.get("", response_model=list[OrderSummary])
def admin_list_orders(
    status: OrderStatus | None = None,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
) -> list[OrderSummary]:
    orders = order_service.list_orders_for_admin(db, status)
    return [OrderSummary.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
def admin_get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
) -> OrderResponse:
    order = order_service.get_order_for_admin(db, order_id)
    return OrderResponse.model_validate(order)


@router.patch("/{order_id}/status", response_model=OrderResponse)
def admin_update_order_status(
    order_id: int,
    payload: AdminOrderStatusUpdateRequest,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
) -> OrderResponse:
    order = order_service.admin_update_order_status(db, order_id, payload.order_status)
    return OrderResponse.model_validate(order)
