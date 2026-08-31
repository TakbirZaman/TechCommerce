"""
Celery application config (spec section 24).

Training, feature generation, profile updates, analytics aggregation, and
periodic model evaluation all run here — never inline in an HTTP request
handler. Broker/backend URLs are read from environment variables so this
can point at the platform's existing Redis instance without code changes.
"""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "intelligence_system",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["celery_app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Periodic jobs (spec section 24 & 26). Schedules are starting points —
# tune once real traffic/data volume is known.
celery_app.conf.beat_schedule = {
    "aggregate-analytics-hourly": {
        "task": "celery_app.tasks.aggregate_analytics",
        "schedule": crontab(minute=0),
    },
    "evaluate-active-models-daily": {
        "task": "celery_app.tasks.evaluate_active_models",
        "schedule": crontab(hour=3, minute=0),
    },
    "refresh-user-profiles-nightly": {
        "task": "celery_app.tasks.refresh_all_user_profiles",
        "schedule": crontab(hour=2, minute=0),
    },
}
