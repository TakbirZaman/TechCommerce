"""
Admin Order management routes.

Requires admin authentication (admin@gmail.com / admin123).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin, AdminUser
from app.core.database import get_db
from app.models.order import Order, OrderStatus
from app.schemas.order import AdminOrderStatusUpdateRequest, OrderResponse

router = APIRouter(prefix="/api/v1/admin/orders", tags=["admin", "orders"])


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int


@router.get("", response_model=OrderListResponse)
def list_orders(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """List all orders (admin only)."""
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=len(orders),
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Get order details (admin only)."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return OrderResponse.model_validate(order)


@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    payload: AdminOrderStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Update order status (admin only)."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    from app.services.order_state_machine import transition_order_status
    transition_order_status(db, order, payload.order_status)

    return OrderResponse.model_validate(order)
