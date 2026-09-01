import logging

from app.core.database import SessionLocal
from app.models.order import Order
from app.services.invoice_service import generate_invoice_for_order
from app.tasks.celery_app import celery_app

logger = logging.getLogger("commerce.tasks.invoice")


@celery_app.task(name="app.tasks.invoice_tasks.generate_invoice_task", bind=True, max_retries=3)
def generate_invoice_task(self, order_id: int) -> None:
    db = SessionLocal()
    try:
        order = db.get(Order, order_id)
        if order is None:
            logger.error("generate_invoice_task: order %s not found", order_id)
            return
        generate_invoice_for_order(db, order)
    except Exception as exc:  # noqa: BLE001
        logger.exception("generate_invoice_task failed for order %s", order_id)
        raise self.retry(exc=exc, countdown=30) from exc
    finally:
        db.close()
