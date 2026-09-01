"""
Payment service (Sections 11-19).

This is the ONLY module that:
  - resolves a PaymentMethod -> PaymentProvider,
  - processes gateway callbacks,
  - decides when an Order moves PAYMENT_PENDING -> PAID,
  - triggers inventory finalization + invoice generation on success.

order_service / checkout_service never talk to bkash.py/nagad.py/sslcommerz.py
directly (Section 11's "order service must not contain gateway-specific code").
"""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import OrderNotFoundError, PaymentError
from app.models.order import Order, OrderStatus
from app.models.order import PaymentStatus as OrderPaymentStatus
from app.models.payment import Payment, PaymentGateway, PaymentStatus, ProcessedCallback
from app.payments.base import PaymentProvider
from app.payments.bkash import BkashPaymentProvider
from app.payments.nagad import NagadPaymentProvider
from app.payments.sslcommerz import SslCommerzPaymentProvider
from app.services import inventory_service
from app.services.order_state_machine import transition_order_status

_PROVIDERS: dict[PaymentGateway, type[PaymentProvider]] = {
    PaymentGateway.BKASH: BkashPaymentProvider,
    PaymentGateway.NAGAD: NagadPaymentProvider,
    PaymentGateway.SSLCOMMERZ: SslCommerzPaymentProvider,
}


def _resolve_provider(gateway: PaymentGateway) -> PaymentProvider:
    provider_cls = _PROVIDERS.get(gateway)
    if provider_cls is None:
        raise PaymentError(f"Unsupported payment gateway: {gateway}")
    return provider_cls()


def initiate_payment_for_order(db: Session, order: Order) -> Payment:
    gateway = PaymentGateway(order.payment_method.value)
    provider = _resolve_provider(gateway)

    result = provider.initiate_payment(
        merchant_reference=order.order_number,
        amount=order.total_amount,
        currency="BDT",
        customer_phone=order.shipping_phone,
    )

    payment = Payment(
        order_id=order.id,
        gateway=gateway,
        merchant_reference=result.merchant_reference,
        transaction_id=result.gateway_transaction_id,
        amount=order.total_amount,
        currency="BDT",
        status=PaymentStatus.INITIATED,
        gateway_response_reference=result.raw_response,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def _order_items_as_tuples(order: Order) -> list[tuple[int, int]]:
    return [(item.product_id, item.quantity) for item in order.items]


def _mark_order_paid(db: Session, order: Order) -> None:
    """
    Successful-payment flow (Section 19):
    Payment SUCCESS -> Order PAID -> inventory finalized -> invoice queued -> notification queued.
    """
    transition_order_status(db, order, OrderStatus.PAID)
    order.payment_status = OrderPaymentStatus.PAID

    inventory_service.finalize_order_items(db, _order_items_as_tuples(order))

    db.flush()

    # Invoice generation and notifications are queued as background work
    # (Celery) rather than run inline in the request/callback path, so a
    # slow PDF render or SMTP call never blocks the payment callback
    # response. See app/tasks/invoice_tasks.py and notification_tasks.py.
    try:
        from app.tasks.invoice_tasks import generate_invoice_task
        from app.tasks.notification_tasks import send_payment_confirmation_task

        generate_invoice_task.delay(order.id)
        send_payment_confirmation_task.delay(order.id)
    except Exception:
        # Celery broker may be unavailable in dev/test environments; the
        # payment itself must still succeed. A reconciliation job
        # (Section 29) sweeps PAID orders without invoices periodically.
        pass


def _mark_order_payment_failed(db: Session, order: Order) -> None:
    order.payment_status = OrderPaymentStatus.FAILED
    inventory_service.release_order_items(db, _order_items_as_tuples(order))
    db.flush()


def process_callback(db: Session, gateway: PaymentGateway, payload: dict) -> dict:
    """
    Idempotent callback processing (Section 16-17).

    dedupe_key is derived BEFORE any side effect. If a row already exists
    for this key, the callback is a replay: return the stored result and
    do nothing else (no double order-paid, no double inventory deduction,
    no double invoice).
    """
    provider = _resolve_provider(gateway)

    if not provider.verify_callback_signature(payload):
        raise PaymentError("Callback failed signature/shape validation")

    # Identify which of our Payment rows this callback refers to.
    merchant_reference = (
        payload.get("merchantInvoiceNumber")  # bKash
        or payload.get("orderId")  # Nagad
        or payload.get("tran_id")  # SSLCommerz
    )
    gateway_ref = (
        payload.get("paymentID")  # bKash
        or payload.get("paymentRefId")  # Nagad
        or payload.get("val_id")  # SSLCommerz
        or merchant_reference
    )

    dedupe_key = f"{gateway.value}:{gateway_ref}"

    existing = db.execute(
        select(ProcessedCallback).where(ProcessedCallback.dedupe_key == dedupe_key)
    ).scalar_one_or_none()
    if existing is not None:
        return {"status": existing.result_status, "duplicate": True}

    payment = db.execute(
        select(Payment).where(Payment.merchant_reference == merchant_reference)
    ).scalar_one_or_none()
    if payment is None:
        raise PaymentError(f"No payment found for reference {merchant_reference}")

    order = db.get(Order, payment.order_id)
    if order is None:
        raise OrderNotFoundError(f"Order for payment {payment.id} not found")

    # Server-side verification against the gateway — never trust the
    # callback body alone (Section 17-19).
    verification = provider.verify_payment(gateway_transaction_id=gateway_ref)

    if verification.success and verification.amount == order.total_amount:
        payment.status = PaymentStatus.SUCCESS
        payment.transaction_id = verification.gateway_transaction_id
        payment.gateway_response_reference = verification.raw_response
        payment.paid_at = datetime.now(UTC)
        _mark_order_paid(db, order)
        result_status = "SUCCESS"
    else:
        payment.status = PaymentStatus.FAILED
        payment.gateway_response_reference = verification.raw_response
        _mark_order_payment_failed(db, order)
        result_status = "FAILED"

    db.add(
        ProcessedCallback(
            dedupe_key=dedupe_key,
            gateway=gateway,
            payment_id=payment.id,
            result_status=result_status,
        )
    )
    db.commit()

    return {"status": result_status, "duplicate": False, "order_number": order.order_number}
