"""
Celery configuration for SwarmMind.

Handles background task processing, scheduled workflows,
and distributed agent execution.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "swarmmind",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.agent_tasks",
        "app.tasks.workflow_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.task_timeout_seconds,
    worker_prefetch_multiplier=1,
    worker_concurrency=settings.celery_worker_concurrency,
    broker_connection_retry_on_startup=True,
    result_expires=3600 * 24,  # Results expire after 24 hours
)

celery_app.autodiscover_tasks()
