import os

from celery import Celery

from app.db import SessionLocal  # noqa: F401  (import ensures .env is loaded before os.getenv below)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "0") == "1"

celery_app = Celery("narrative_clustering", broker=REDIS_URL, backend=REDIS_URL, include=["app.tasks"])
celery_app.conf.update(
    task_always_eager=TASK_ALWAYS_EAGER,
    task_eager_propagates=TASK_ALWAYS_EAGER,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
