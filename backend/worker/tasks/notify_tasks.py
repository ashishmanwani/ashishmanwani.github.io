"""
Notification tasks.
check_and_notify() — evaluates all active alerts for a product after a price update.
send_telegram_alert() — sends the actual Telegram message.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.db.session import AsyncSessionLocal
from api.models.alert import Alert
from api.models.price_record import PriceRecord
from api.models.product import Product
from api.models.scrape_job import NotificationLog
from api.services.alert_service import should_notify
from notifications.deduplicator import is_duplicate, mark_sent
from notifications.telegram import TelegramNotifier
from notifications.templates import build_price_drop_message
from worker.celery_app import app

logger = logging.getLogger(__name__)
telegram = TelegramNotifier()


@app.task(
    name="worker.tasks.notify_tasks.check_and_notify",
    queue="notifications",
    rate_limit="60/m",
)
def check_and_notify(product_id: str, price_record_id: int):
    """
    Check all active alerts for the given product against the new price record.
    Sends Telegram notifications for triggered alerts.
    """
    async def _check():
        async with AsyncSessionLocal() as db:
            # Load product with price record
            product_result = await db.execute(
                select(Product).where(Product.id == uuid.UUID(product_id))
            )
            product = product_result.scalar_one_or_none()
            if not product:
                return

            pr_result = await db.execute(
                select(PriceRecord).where(PriceRecord.id == price_record_id)
            )
            price_record = pr_result.scalar_one_or_none()
            if not price_record or price_record.is_out_of_stock:
                return

            # Load all active alerts for this product with user eager-loaded
            alerts_result = await db.execute(
                select(Alert)
                .options(selectinload(Alert.user), selectinload(Alert.product))
                .where(
                    Alert.product_id == product.id,
                    Alert.is_active == True,  # noqa: E712
                )
            )
            alerts = alerts_result.scalars().all()

            for alert in alerts:
                if not should_notify(alert, price_record):
                    continue

                user = alert.user
                if not user.telegram_chat_id:
                    logger.debug(f"Alert {alert.id}: user has no Telegram linked, skipping")
                    continue

                # Deduplication — prevent re-sending same price drop
                price_cents = int(float(price_record.price or 0) * 100)
                if is_duplicate(str(alert.id), price_cents):
                    logger.debug(f"Alert {alert.id}: duplicate notification suppressed")
                    continue

                # Enqueue individual notification send
                send_telegram_alert.apply_async(
                    args=[str(alert.id), price_record_id, user.telegram_chat_id],
                    queue="notifications",
                )

    asyncio.run(_check())


@app.task(
    name="worker.tasks.notify_tasks.send_telegram_alert",
    queue="notifications",
    bind=True,
    max_retries=5,
)
def send_telegram_alert(self, alert_id: str, price_record_id: int, chat_id: int):
    """Send a Telegram price drop alert for a specific alert + price record."""
    async def _send():
        async with AsyncSessionLocal() as db:
            alert_result = await db.execute(
                select(Alert)
                .options(selectinload(Alert.product))
                .where(Alert.id == uuid.UUID(alert_id))
            )
            alert = alert_result.scalar_one_or_none()
            if not alert:
                return

            pr_result = await db.execute(
                select(PriceRecord).where(PriceRecord.id == price_record_id)
            )
            price_record = pr_result.scalar_one_or_none()
            if not price_record:
                return

            message = build_price_drop_message(alert, price_record)

            try:
                msg_id = await telegram.send_message(chat_id=chat_id, text=message)

                # Log successful notification
                log = NotificationLog(
                    alert_id=alert.id,
                    price_record_id=price_record_id,
                    channel="telegram",
                    status="sent",
                    telegram_message_id=msg_id,
                )
                db.add(log)

                # Update alert stats
                from datetime import datetime, timezone
                alert.last_notified_at = datetime.now(tz=timezone.utc)
                alert.triggered_count = (alert.triggered_count or 0) + 1

                # Mark dedup key
                price_cents = int(float(price_record.price or 0) * 100)
                mark_sent(alert_id, price_cents)

                await db.commit()
                logger.info(f"Sent Telegram alert to chat_id={chat_id} for alert={alert_id}")

            except Exception as e:
                error_str = str(e)
                # Handle Telegram rate limit (HTTP 429)
                if "429" in error_str or "Too Many Requests" in error_str:
                    import re
                    retry_after_match = re.search(r"retry after (\d+)", error_str, re.IGNORECASE)
                    retry_after = int(retry_after_match.group(1)) + 1 if retry_after_match else 30
                    raise self.retry(exc=e, countdown=retry_after)

                log = NotificationLog(
                    alert_id=alert.id,
                    price_record_id=price_record_id,
                    channel="telegram",
                    status="failed",
                )
                db.add(log)
                await db.commit()
                logger.error(f"Failed to send Telegram alert: {e}")
                raise

    asyncio.run(_send())
