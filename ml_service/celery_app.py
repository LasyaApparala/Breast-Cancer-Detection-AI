"""
Celery application configuration for the ML service.

Broker: Redis (CELERY_BROKER_URL)
Result backend: Redis (CELERY_RESULT_BACKEND)
Queue: classification_tasks

Requirements: 11.1
"""

import os
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "ml_service",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
)

celery_app.conf.update(
    task_queues={"classification_tasks": {"exchange": "classification_tasks"}},
    task_default_queue="classification_tasks",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
    # Celery beat schedule: run override rate check daily at midnight UTC
    beat_schedule={
        "check-retraining-trigger-daily": {
            "task": "ml_service.tasks.check_retraining_trigger_task",
            "schedule": crontab(hour=0, minute=0),
        },
    },
    timezone="UTC",
)
