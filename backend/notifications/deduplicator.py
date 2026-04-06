"""
Notification deduplicator.
Prevents sending the same price drop alert twice for the same alert + price.
Uses Redis with a 6-hour TTL.
"""

import logging
from datetime import timedelta

import redis

from api.config import settings

logger = logging.getLogger(__name__)

DEDUP_TTL = int(timedelta(hours=6).total_seconds())


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def is_duplicate(alert_id: str, price_cents: int) -> bool:
    """
    Returns True if this alert was already notified at this price within the TTL window.
    price_cents: price in integer cents (e.g. ₹199.90 → 19990) for exact key matching.
    """
    try:
        r = _get_redis()
        key = f"notify:dedup:{alert_id}:{price_cents}"
        return r.exists(key) == 1
    except Exception as e:
        logger.warning(f"Deduplicator check error: {e}")
        return False  # Fail open


def mark_sent(alert_id: str, price_cents: int) -> None:
    """Mark that a notification was sent for this alert + price."""
    try:
        r = _get_redis()
        key = f"notify:dedup:{alert_id}:{price_cents}"
        r.setex(key, DEDUP_TTL, "1")
    except Exception as e:
        logger.warning(f"Deduplicator mark error: {e}")
