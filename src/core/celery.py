from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging as celery_setup_logging_signal

from src.core.config import settings
from src.core.logging_config import setup_logging


@celery_setup_logging_signal.connect
def _configure_celery_logging(*args, **kwargs):
    """Hand logging config fully to our JSON/rotating-file setup instead of
    letting Celery install its own stdout-only formatter."""
    setup_logging()


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
            "schedule": crontab(hour=0, minute=5),
        }
    }
)
