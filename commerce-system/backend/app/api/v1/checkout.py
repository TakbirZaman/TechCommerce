"""
Checkout API routes (Section 6-10).

Guest checkout - no authentication required.
Users provide email, phone, name, address directly.
"""
from fastapi import APIRouter, Depends, Request

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.order import CheckoutRequest, OrderResponse
from app.services import checkout_service

router = APIRouter(prefix="/api/v1/checkout", tags=["checkout"])


def get_session_id(request: Request) -> str:
    """Get session_id from cookie."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        import secrets
        session_id = secrets.token_urlsafe(32)
    return session_id


@router.post("", response_model=OrderResponse)
def checkout(
    payload: CheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Complete checkout - no login required.
    Users provide:
    - email, phone, name, address
    - payment method
    - optional discount code
    """
    session_id = get_session_id(request)
    return checkout_service.checkout(db, session_id, payload)
