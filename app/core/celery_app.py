from celery import Celery
import os

# Use Redis as Broker and Backend
# Default to localhost if not set in env
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "safex_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker Optimization
    worker_concurrency=4,  # Adjust based on CPU cores
    worker_prefetch_multiplier=1,  # Good for long running tasks (monitoring)
)

if __name__ == "__main__":
    celery_app.start()
