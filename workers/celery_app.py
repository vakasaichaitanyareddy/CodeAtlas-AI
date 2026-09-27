import os
import redis.connection
import redis.utils

# Default to RESP2 for broad compatibility across local native Redis and Docker Redis
redis.connection.DEFAULT_RESP_VERSION = 2
redis.utils.DEFAULT_RESP_VERSION = 2

from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery(
    "codeatlas_workers",
    broker=broker_url,
    backend=result_backend,
    include=["workers.tasks.ingestion"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
