from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "commerce",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.invoice_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.reconciliation_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "reconcile-pending-payments-every-10-min": {
        "task": "app.tasks.reconciliation_tasks.reconcile_pending_payments",
        "schedule": 600.0,
    },
    "sweep-paid-orders-missing-invoices-every-15-min": {
        "task": "app.tasks.reconciliation_tasks.sweep_missing_invoices",
        "schedule": 900.0,
    },
}
