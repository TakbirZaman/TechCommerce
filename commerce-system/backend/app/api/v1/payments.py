"""
Payment API routes.

- POST /api/v1/payments/initiate requires order number (no auth).
- Gateway callbacks are public (gateway calls them server-to-server).
"""
import json

from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import CommerceError
from app.core.rate_limiter import check_payment_callback_rate_limit
from app.models.payment import PaymentGateway
from app.schemas.payment import PaymentCallbackResult, PaymentInitiateResponse
from app.services import payment_service

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class PaymentInitiateRequest(BaseModel):
    """Simple payment initiation - just order ID."""
    order_id: int


@router.post("/initiate", response_model=PaymentInitiateResponse)
def initiate_payment(
    payload: PaymentInitiateRequest,
    db: Session = Depends(get_db),
):
    """
    Initiate payment for an order.
    No auth required - just provide order ID.
    """
    from app.models.order import Order
    order = db.get(Order, payload.order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    payment = payment_service.initiate_payment_for_order(db, order)

    redirect_url = None
    if payment.gateway_response_reference:
        try:
            raw = json.loads(payment.gateway_response_reference)
            redirect_url = (
                raw.get("bkashURL")
                or raw.get("GatewayPageURL")
                or raw.get("complete", {}).get("callBackUrl")
            )
        except (ValueError, AttributeError):
            redirect_url = None

    return PaymentInitiateResponse(
        payment_id=payment.id,
        redirect_url=redirect_url,
        gateway_transaction_id=payment.transaction_id,
    )


async def _parse_payload(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return await request.json()
    form = await request.form()
    return dict(form)


async def _handle_callback(gateway: PaymentGateway, request: Request, db: Session) -> PaymentCallbackResult:
    # Rate limiting check for payment callbacks
    client_ip = request.client.host if request.client else "unknown"
    if check_payment_callback_rate_limit(gateway.value, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for payment callbacks",
        )

    payload = await _parse_payload(request)
    try:
        result = payment_service.process_callback(db, gateway, payload)
    except CommerceError as exc:
        raise exc
    return PaymentCallbackResult(**result)


@router.post("/bkash/callback", response_model=PaymentCallbackResult)
async def bkash_callback(request: Request, db: Session = Depends(get_db)) -> PaymentCallbackResult:
    return await _handle_callback(PaymentGateway.BKASH, request, db)


@router.post("/nagad/callback", response_model=PaymentCallbackResult)
async def nagad_callback(request: Request, db: Session = Depends(get_db)) -> PaymentCallbackResult:
    return await _handle_callback(PaymentGateway.NAGAD, request, db)


@router.post("/sslcommerz/success", response_model=PaymentCallbackResult)
async def sslcommerz_success(request: Request, db: Session = Depends(get_db)) -> PaymentCallbackResult:
    return await _handle_callback(PaymentGateway.SSLCOMMERZ, request, db)


@router.post("/sslcommerz/ipn", response_model=PaymentCallbackResult)
async def sslcommerz_ipn(request: Request, db: Session = Depends(get_db)) -> PaymentCallbackResult:
    return await _handle_callback(PaymentGateway.SSLCOMMERZ, request, db)


@router.post("/sslcommerz/fail", response_model=PaymentCallbackResult)
async def sslcommerz_fail(request: Request, db: Session = Depends(get_db)) -> PaymentCallbackResult:
    return await _handle_callback(PaymentGateway.SSLCOMMERZ, request, db)


@router.post("/sslcommerz/cancel", response_model=PaymentCallbackResult)
async def sslcommerz_cancel(request: Request, db: Session = Depends(get_db)) -> PaymentCallbackResult:
    return await _handle_callback(PaymentGateway.SSLCOMMERZ, request, db)
