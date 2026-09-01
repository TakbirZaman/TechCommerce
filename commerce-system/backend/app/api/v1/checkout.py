from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.schemas.order import CheckoutRequest, OrderResponse
from app.services import checkout_service

router = APIRouter(prefix="/api/v1/checkout", tags=["checkout"])


@router.post("", response_model=OrderResponse, status_code=201)
def create_checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderResponse:
    order = checkout_service.checkout(db, current_user.id, payload)
    return OrderResponse.model_validate(order)
