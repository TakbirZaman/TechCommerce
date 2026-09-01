"""
Background reconciliation jobs (Section 29).

These exist because a payment callback can be lost (network blip, gateway
retry exhaustion, server restart mid-request) — without a sweep, an order
could sit in PAYMENT_PENDING forever even though the gateway actually
succeeded (or actually failed and stock should be released).
"""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentGateway, PaymentStatus
from app.services import inventory_service, payment_service
from app.services.order_state_machine import transition_order_status
from app.tasks.celery_app import celery_app

logger = logging.getLogger("commerce.tasks.reconciliation")

# Orders left in PAYMENT_PENDING past this window without a resolved
# payment are considered abandoned and released.
RESERVATION_TIMEOUT = timedelta(minutes=30)


@celery_app.task(name="app.tasks.reconciliation_tasks.reconcile_pending_payments")
def reconcile_pending_payments() -> None:
    db = SessionLocal()
    try:
        stale_cutoff = datetime.now(UTC) - RESERVATION_TIMEOUT
        pending_orders = db.execute(
            select(Order).where(
                Order.order_status == OrderStatus.PAYMENT_PENDING,
                Order.created_at < stale_cutoff,
            )
        ).scalars().all()

        for order in pending_orders:
            latest_payment = db.execute(
                select(Payment)
                .where(Payment.order_id == order.id)
                .order_by(Payment.created_at.desc())
            ).scalars().first()

            if latest_payment is None or latest_payment.transaction_id is None:
                _release_and_cancel(db, order)
                continue

            try:
                gateway = PaymentGateway(order.payment_method.value)
                provider = payment_service._resolve_provider(gateway)  # noqa: SLF001 (internal reuse)
                verification = provider.verify_payment(gateway_transaction_id=latest_payment.transaction_id)
            except Exception:
                logger.exception("reconciliation: verify_payment failed for order %s", order.order_number)
                continue

            if verification.success:
                latest_payment.status = PaymentStatus.SUCCESS
                payment_service._mark_order_paid(db, order)  # noqa: SLF001
            else:
                _release_and_cancel(db, order)

            db.commit()
    finally:
        db.close()


def _release_and_cancel(db, order: Order) -> None:
    items = [(item.product_id, item.quantity) for item in order.items]
    inventory_service.release_order_items(db, items)
    transition_order_status(db, order, OrderStatus.CANCELLED)
    db.commit()


@celery_app.task(name="app.tasks.reconciliation_tasks.sweep_missing_invoices")
def sweep_missing_invoices() -> None:
    """Catches PAID orders whose invoice generation task was lost (e.g. broker unavailable at the time)."""
    from app.models.invoice import Invoice
    from app.services.invoice_service import generate_invoice_for_order

    db = SessionLocal()
    try:
        paid_orders = db.execute(select(Order).where(Order.order_status == OrderStatus.PAID)).scalars().all()
        for order in paid_orders:
            has_invoice = db.execute(select(Invoice).where(Invoice.order_id == order.id)).scalar_one_or_none()
            if has_invoice is None:
                try:
                    generate_invoice_for_order(db, order)
                except Exception:
                    logger.exception("sweep_missing_invoices failed for order %s", order.order_number)
    finally:
        db.close()
