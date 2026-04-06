from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Main dispatcher — runs every 15 minutes, enqueues products due for scraping
    "dispatch-scrape-jobs": {
        "task": "worker.tasks.scrape_tasks.dispatch_scrape_jobs",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "maintenance"},
    },
    # Proxy health check — runs every 20 minutes
    "proxy-health-check": {
        "task": "worker.tasks.maintenance_tasks.run_proxy_health_check",
        "schedule": crontab(minute="*/20"),
        "options": {"queue": "maintenance"},
    },
    # Recompute scrape tiers based on price proximity to targets
    "recompute-scrape-tiers": {
        "task": "worker.tasks.maintenance_tasks.recompute_scrape_tiers",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "maintenance"},
    },
    # Clean up old price records (keep 90 days) — runs at 3am daily
    "cleanup-old-records": {
        "task": "worker.tasks.maintenance_tasks.cleanup_old_price_records",
        "schedule": crontab(hour="3", minute="0"),
        "options": {"queue": "maintenance"},
    },
    # Unban expired proxies
    "unban-proxies": {
        "task": "worker.tasks.maintenance_tasks.unban_expired_proxies",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "maintenance"},
    },
    # Load proxy pool on startup if empty
    "refresh-proxy-pool": {
        "task": "worker.tasks.maintenance_tasks.refresh_proxy_pool",
        "schedule": crontab(hour="*/6", minute="0"),  # Every 6 hours
        "options": {"queue": "maintenance"},
    },
}
