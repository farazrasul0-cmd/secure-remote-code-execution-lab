"""Celery Application Configuration for Distributed Task Execution."""

from celery import Celery

from worker.config import worker_settings

# Instantiate Celery application
celery_app = Celery(
    "rce_worker",
    broker=worker_settings.REDIS_URL,
    backend=worker_settings.REDIS_URL,
    include=["worker.tasks.execution"],
)

# Configure Celery execution policies
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Distributed Reliability & Fairness
    task_acks_late=True,  # Acknowledge only after task completes
    task_reject_on_worker_lost=True,  # Re-queue task if worker process terminates abnormally
    worker_prefetch_multiplier=1,  # Strict fair dispatch: 1 task per worker at a time
    task_track_started=True,
    # Result Expiration
    result_expires=3600,
    # Celery Beat Periodic Janitor Schedule
    beat_schedule={
        "reap-orphan-containers-every-30s": {
            "task": "worker.tasks.execution.reap_orphan_containers",
            "schedule": worker_settings.JANITOR_INTERVAL_SECONDS,
        },
    },
)
