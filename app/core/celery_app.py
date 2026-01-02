import os
from pathlib import Path
from celery import Celery
from celery.signals import worker_init
from dotenv import load_dotenv

# Load .env file explicitly with absolute path
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Verify critical environment variables are loaded
if not os.getenv('GOOGLE_API_KEY'):
    print("WARNING: GOOGLE_API_KEY not loaded from .env file!")
    print(f"Tried to load from: {env_path}")
    print(f"File exists: {env_path.exists()}")

from app.core.config import settings

# Import all models to ensure SQLAlchemy relationships are resolved
# This must happen before Celery tasks are loaded
import app.models  # noqa: F401

# Use Redis as Broker and Backend (from settings which loads from .env)
REDIS_URL = settings.REDIS_URL

celery_app = Celery(
    "xmonitor_worker",
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


@worker_init.connect
def setup_worker_logging(**kwargs):
    """Initialize logging when the Celery worker starts"""
    from app.worker.utils.logging_config import setup_logging
    setup_logging(
        level=settings.LOG_LEVEL,
        log_file="logs/xmonitor-worker.log",
        console=True
    )


if __name__ == "__main__":
    celery_app.start()
