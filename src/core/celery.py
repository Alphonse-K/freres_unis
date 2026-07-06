from celery import Celery
from celery.schedules import crontab
from src.core.config import settings


celery_app = Celery(
    "Client_balance",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

import src.tasks.scheduled_tasks      # ← add this

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "src.tasks.*": {"queue": "balance_incremental"}
    },
    beat_schedule={
        "increment-partner-balances-midnight": {
            "task": "src.tasks.scheduled_tasks.increment_partner_balances",
            "schedule": crontab(hour=20, minute=3),
        }
    }
)
