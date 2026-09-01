from app.services import notification_service
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.notification_tasks.send_order_confirmation_task")
def send_order_confirmation_task(order_id: int) -> None:
    notification_service.send_order_confirmation(order_id)


@celery_app.task(name="app.tasks.notification_tasks.send_payment_confirmation_task")
def send_payment_confirmation_task(order_id: int) -> None:
    notification_service.send_payment_confirmation(order_id)


@celery_app.task(name="app.tasks.notification_tasks.send_payment_failed_task")
def send_payment_failed_task(order_id: int) -> None:
    notification_service.send_payment_failed(order_id)


@celery_app.task(name="app.tasks.notification_tasks.send_order_shipped_task")
def send_order_shipped_task(order_id: int) -> None:
    notification_service.send_order_shipped(order_id)


@celery_app.task(name="app.tasks.notification_tasks.send_order_delivered_task")
def send_order_delivered_task(order_id: int) -> None:
    notification_service.send_order_delivered(order_id)
