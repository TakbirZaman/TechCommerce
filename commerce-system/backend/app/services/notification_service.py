"""
Notification service foundation (Section 30).

Order/payment routes and services never construct emails/SMS themselves —
they call these functions, which are in turn called from Celery tasks
(app/tasks/notification_tasks.py) so sending never blocks a request.

No concrete email/SMS provider is wired up yet (out of scope for this
pass) — these log/no-op today and are the seam where SES/SendGrid/Twilio
etc. get plugged in later. Keeping the seam here (not inside routes) is
what the spec asks for.
"""
import logging

logger = logging.getLogger("commerce.notifications")


def send_order_confirmation(order_id: int) -> None:
    logger.info("notification.order_confirmation order_id=%s", order_id)


def send_payment_confirmation(order_id: int) -> None:
    logger.info("notification.payment_confirmation order_id=%s", order_id)


def send_payment_failed(order_id: int) -> None:
    logger.info("notification.payment_failed order_id=%s", order_id)


def send_order_processing(order_id: int) -> None:
    logger.info("notification.order_processing order_id=%s", order_id)


def send_order_shipped(order_id: int) -> None:
    logger.info("notification.order_shipped order_id=%s", order_id)


def send_order_delivered(order_id: int) -> None:
    logger.info("notification.order_delivered order_id=%s", order_id)
