"""
Payment API routes.

- POST /api/v1/payments/initiate requires customer auth and re-validates
  order ownership before calling out to a gateway (IDOR protection).
- The gateway callback endpoints (/payments/{gateway}/callback) are public
  by necessity (gateways call them server-to-server / via browser redirect)
  but every one of them runs through payment_service.process_callback(),
  which enforces signature/shape checks + idempotency + server-side
  verification before trusting anything in the payload (Sections 16-17).
"""
import json

from fastapi import APIRouter, Depends, Request

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import CommerceError
from app.core.security import CurrentUser, get_current_user
from app.models.payment import PaymentGateway
from app.schemas.payment import PaymentCallbackResult, PaymentInitiateRequest, PaymentInitiateResponse
from app.services import order_service, payment_service

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("/initiate", response_model=PaymentInitiateResponse)
def initiate_payment(
    payload: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaymentInitiateResponse:
    # get_order_for_customer enforces ownership — a user can't initiate
    # payment against someone else's order (IDOR protection, Section 31).
    order = order_service.get_order_for_customer(db, current_user.id, payload.order_id)

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
    payload = await _parse_payload(request)
    try:
        result = payment_service.process_callback(db, gateway, payload)
    except CommerceError as exc:
        # Surface as a normal error response rather than a 500; the
        # exception handler registered in app/api/error_handlers.py maps
        # CommerceError subclasses to the right status code.
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
    """IPN is the server-to-server notification SSLCommerz recommends relying on (Section 17)."""
    return await _handle_callback(PaymentGateway.SSLCOMMERZ, request, db)


@router.post("/sslcommerz/fail", response_model=PaymentCallbackResult)
async def sslcommerz_fail(request: Request, db: Session = Depends(get_db)) -> PaymentCallbackResult:
    return await _handle_callback(PaymentGateway.SSLCOMMERZ, request, db)


@router.post("/sslcommerz/cancel", response_model=PaymentCallbackResult)
async def sslcommerz_cancel(request: Request, db: Session = Depends(get_db)) -> PaymentCallbackResult:
    return await _handle_callback(PaymentGateway.SSLCOMMERZ, request, db)
