"""
Core scraping tasks.
dispatch_scrape_jobs() — runs every 15min via Beat, enqueues due products.
scrape_product()       — executed by Celery workers, runs the full scrape pipeline.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import redis as redis_lib
from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from api.config import settings
from api.db.session import AsyncSessionLocal
from api.models.price_record import PriceRecord
from api.models.product import Product
from api.models.scrape_job import ScrapeJob
from api.services.alert_service import TIER_INTERVALS_SECONDS, compute_scrape_tier
from proxy.manager import proxy_manager
from scraper.registry import get_scraper
from worker.celery_app import app

logger = logging.getLogger(__name__)

TIER_QUEUE_MAP = {
    "critical": "scrape_critical",
    "high": "scrape_critical",
    "normal": "scrape_normal",
    "low": "scrape_normal",
}


def _get_redis():
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


@app.task(name="worker.tasks.scrape_tasks.dispatch_scrape_jobs", queue="maintenance")
def dispatch_scrape_jobs():
    """
    Query products due for scraping and enqueue scrape tasks.
    Runs every 15 minutes via Celery Beat.
    """
    async def _dispatch():
        async with AsyncSessionLocal() as db:
            now = datetime.now(tz=timezone.utc)
            result = await db.execute(
                select(Product)
                .options(selectinload(Product.alerts))
                .where(Product.is_active == True)  # noqa: E712
            )
            products = result.scalars().all()

            r = _get_redis()
            enqueued = 0

            for product in products:
                tier = product.scrape_tier
                interval = TIER_INTERVALS_SECONDS.get(tier, TIER_INTERVALS_SECONDS["normal"])

                # Check if product is due for scraping
                if product.last_scraped_at:
                    elapsed = (now - product.last_scraped_at).total_seconds()
                    if elapsed < interval:
                        continue

                # Dedup: skip if a scrape job is already queued for this product
                lock_key = f"scrape:lock:{product.id}"
                acquired = r.set(lock_key, "1", ex=interval, nx=True)
                if not acquired:
                    continue

                queue = TIER_QUEUE_MAP.get(tier, "scrape_normal")
                priority = {"critical": 1, "high": 2, "normal": 5, "low": 9}.get(tier, 5)

                scrape_product.apply_async(
                    args=[str(product.id)],
                    queue=queue,
                    priority=priority,
                )
                enqueued += 1

            logger.info(f"dispatch_scrape_jobs: enqueued {enqueued} scrape tasks")
            return enqueued

    return asyncio.run(_dispatch())


@app.task(
    name="worker.tasks.scrape_tasks.scrape_product",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min base delay
    acks_late=True,
)
def scrape_product(self, product_id: str):
    """
    Execute a scrape for a single product and store the result.
    Triggered by dispatch_scrape_jobs() or directly via force_scrape.
    """
    async def _scrape():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product)
                .options(selectinload(Product.alerts))
                .where(Product.id == uuid.UUID(product_id))
            )
            product = result.scalar_one_or_none()
            if not product:
                logger.error(f"Product {product_id} not found")
                return

            # Create scrape job record
            job = ScrapeJob(
                product_id=product.id,
                status="running",
                celery_task_id=self.request.id,
                started_at=datetime.now(tz=timezone.utc),
                priority={"critical": 1, "high": 2, "normal": 5, "low": 9}.get(product.scrape_tier, 5),
            )
            db.add(job)
            await db.commit()

            try:
                # Get scraper for the site
                scraper = get_scraper(product.site)

                # Get best proxy for this site
                proxy_model = proxy_manager.get_proxy(product.site)
                proxy_dict = proxy_model.as_dict if proxy_model else None

                # Execute the scrape
                import time
                start_time = time.monotonic()
                scrape_result = await scraper.scrape(product.canonical_url, proxy_dict)
                elapsed_ms = (time.monotonic() - start_time) * 1000

                # Report proxy outcome
                if proxy_model:
                    if scrape_result.is_captcha:
                        proxy_manager.report_captcha(proxy_model, product.site)
                    elif scrape_result.success:
                        proxy_manager.report_success(proxy_model, product.site, elapsed_ms)
                    else:
                        proxy_manager.report_failure(proxy_model, product.site)

                # Handle CAPTCHA with retry
                if scrape_result.is_captcha:
                    job.status = "captcha_blocked"
                    job.error_message = "CAPTCHA detected"
                    job.attempts = (job.attempts or 0) + 1
                    await db.commit()
                    raise self.retry(
                        exc=Exception("CAPTCHA"),
                        countdown=min(300 * (2 ** self.request.retries), 3600),
                    )

                # Store price record
                price_record = PriceRecord(
                    product_id=product.id,
                    price=scrape_result.price,
                    is_out_of_stock=scrape_result.is_out_of_stock,
                    extraction_method=scrape_result.extraction_method,
                    confidence=scrape_result.confidence,
                    raw_metadata={
                        **scrape_result.metadata,
                        "response_time_ms": elapsed_ms,
                        "proxy_id": proxy_model.id if proxy_model else "direct",
                    },
                )
                db.add(price_record)

                # Update product
                if scrape_result.success:
                    product.current_price = scrape_result.price
                    if scrape_result.title and not product.title:
                        product.title = scrape_result.title
                    if scrape_result.image_url and not product.image_url:
                        product.image_url = scrape_result.image_url

                product.last_scraped_at = datetime.now(tz=timezone.utc)

                # Recompute scrape tier
                new_tier = compute_scrape_tier(product)
                product.scrape_tier = new_tier

                job.status = "done" if scrape_result.success else "failed"
                job.completed_at = datetime.now(tz=timezone.utc)
                if not scrape_result.success:
                    job.error_message = scrape_result.error

                await db.commit()
                await db.refresh(price_record)

                # Trigger notification check if price was successfully extracted
                if scrape_result.success and not scrape_result.is_out_of_stock:
                    from worker.tasks.notify_tasks import check_and_notify
                    check_and_notify.apply_async(
                        args=[str(product.id), price_record.id],
                        queue="notifications",
                    )

                logger.info(
                    f"Scraped {product.site} product {product_id}: "
                    f"price={scrape_result.price} method={scrape_result.extraction_method} "
                    f"confidence={scrape_result.confidence:.2f}"
                )

            except Exception as e:
                if "CAPTCHA" in str(e):
                    raise
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.now(tz=timezone.utc)
                await db.commit()
                logger.error(f"Scrape failed for product {product_id}: {e}")
                raise

    asyncio.run(_scrape())
