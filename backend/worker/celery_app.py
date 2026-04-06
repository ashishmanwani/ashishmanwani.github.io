from celery import Celery

from api.config import settings

app = Celery(
    "price_tracker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "worker.tasks.scrape_tasks",
        "worker.tasks.notify_tasks",
        "worker.tasks.maintenance_tasks",
    ],
)

app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,

    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker (important for browser tasks)

    # Result TTL
    result_expires=3600,

    # Queues
    task_queues={
        "scrape_critical": {"exchange": "scrape_critical", "routing_key": "scrape.critical"},
        "scrape_normal": {"exchange": "scrape_normal", "routing_key": "scrape.normal"},
        "notifications": {"exchange": "notifications", "routing_key": "notifications"},
        "maintenance": {"exchange": "maintenance", "routing_key": "maintenance"},
    },
    task_default_queue="scrape_normal",
    task_default_exchange="scrape_normal",
    task_default_routing_key="scrape.normal",

    # Beat schedule
    beat_schedule_filename="/app/celerybeat/celerybeat-schedule",
)

# Import beat schedule
from worker.beat_schedule import CELERY_BEAT_SCHEDULE  # noqa: E402
app.conf.beat_schedule = CELERY_BEAT_SCHEDULE
