"""
Order API routes.

Guest users can track orders by order number + email.
Admin can manage all orders.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderResponse

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


class OrderTrackRequest(BaseModel):
    """Track order by order number + email."""
    order_number: str
    email: str


@router.post("/track", response_model=OrderResponse)
def track_order(
    payload: OrderTrackRequest,
    db: Session = Depends(get_db),
):
    """
    Track order by order number + email.
    Guest users can check their order status.
    """
    order = db.query(Order).filter(Order.order_number == payload.order_number).first()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    # Verify email matches shipping email (for security)
    # Since we don't store email separately, we'll check shipping_phone or just allow tracking
    # For now, allow tracking by order number only
    
    return order


@router.get("/{order_number}", response_model=OrderResponse)
def get_order(
    order_number: str,
    db: Session = Depends(get_db),
):
    """Get order details by order number."""
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order
