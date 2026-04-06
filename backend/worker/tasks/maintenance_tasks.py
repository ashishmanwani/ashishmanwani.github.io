"""
Maintenance tasks — run by the maintenance worker.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from api.config import settings
from api.db.session import AsyncSessionLocal
from api.models.price_record import PriceRecord
from api.models.product import Product
from api.models.scrape_job import ScrapeJob
from api.services.alert_service import compute_scrape_tier
from worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="worker.tasks.maintenance_tasks.cleanup_old_price_records", queue="maintenance")
def cleanup_old_price_records(days: int = 90):
    """Delete price records older than `days` days."""
    async def _cleanup():
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(PriceRecord).where(PriceRecord.scraped_at < cutoff)
            )
            await db.commit()
            logger.info(f"Deleted {result.rowcount} price records older than {days} days")
            return result.rowcount

    return asyncio.run(_cleanup())


@app.task(name="worker.tasks.maintenance_tasks.recompute_scrape_tiers", queue="maintenance")
def recompute_scrape_tiers():
    """Recompute scrape tier for all active products based on current prices vs targets."""
    async def _recompute():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product)
                .options(selectinload(Product.alerts))
                .where(Product.is_active == True)  # noqa: E712
            )
            products = result.scalars().all()
            updated = 0
            for product in products:
                new_tier = compute_scrape_tier(product)
                if new_tier != product.scrape_tier:
                    product.scrape_tier = new_tier
                    updated += 1
            await db.commit()
            logger.info(f"Recomputed scrape tiers: {updated} products updated")
            return updated

    return asyncio.run(_recompute())


@app.task(name="worker.tasks.maintenance_tasks.run_proxy_health_check", queue="maintenance")
def run_proxy_health_check():
    """Run health check for all proxies in the pool."""
    from proxy.health_checker import run_health_check_all
    return run_health_check_all()


@app.task(name="worker.tasks.maintenance_tasks.unban_expired_proxies", queue="maintenance")
def unban_expired_proxies():
    """Unban proxies whose ban period has expired."""
    from proxy.manager import proxy_manager
    count = proxy_manager.unban_expired()
    logger.info(f"Unbanned {count} expired proxies")
    return count


@app.task(name="worker.tasks.maintenance_tasks.refresh_proxy_pool", queue="maintenance")
def refresh_proxy_pool():
    """Load/refresh proxy pool based on configured provider."""
    from api.config import settings

    if settings.PROXY_PROVIDER == "webshare":
        from proxy.sources.webshare import fetch_and_load_proxies
        count = fetch_and_load_proxies()
    elif settings.PROXY_PROVIDER == "static_file":
        from proxy.sources.static_list import load_from_file
        count = load_from_file(settings.PROXY_STATIC_FILE_PATH)
    else:
        logger.info("Proxy provider is 'none', skipping pool refresh")
        count = 0

    return {"loaded": count, "provider": settings.PROXY_PROVIDER}


@app.task(name="worker.tasks.maintenance_tasks.reset_stale_scrape_jobs", queue="maintenance")
def reset_stale_scrape_jobs(stale_minutes: int = 15):
    """Reset scrape jobs stuck in 'running' state (worker crash recovery)."""
    async def _reset():
        cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=stale_minutes)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ScrapeJob).where(
                    ScrapeJob.status == "running",
                    ScrapeJob.started_at < cutoff,
                )
            )
            stale_jobs = result.scalars().all()
            for job in stale_jobs:
                job.status = "pending"
                job.started_at = None
                job.error_message = "Reset: worker died mid-task"
            await db.commit()
            if stale_jobs:
                logger.warning(f"Reset {len(stale_jobs)} stale scrape jobs")
            return len(stale_jobs)

    return asyncio.run(_reset())
