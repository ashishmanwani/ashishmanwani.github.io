"""
Per-user Telegram rate limiter using Redis.
Enforces: max 1 message per second per chat_id.
"""

import logging

import redis

from api.config import settings

logger = logging.getLogger(__name__)

RATE_WINDOW_SECONDS = 1  # 1 message per second per chat
MAX_PER_WINDOW = 1


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def is_rate_limited(chat_id: int) -> bool:
    """Returns True if the chat_id has hit the rate limit."""
    try:
        r = _get_redis()
        key = f"telegram:rate:{chat_id}"
        current = r.get(key)
        if current and int(current) >= MAX_PER_WINDOW:
            return True
        return False
    except Exception as e:
        logger.warning(f"Rate limiter error: {e}")
        return False  # Fail open — allow sending


def record_send(chat_id: int) -> None:
    """Record that a message was sent to this chat_id."""
    try:
        r = _get_redis()
        key = f"telegram:rate:{chat_id}"
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, RATE_WINDOW_SECONDS)
        pipe.execute()
    except Exception as e:
        logger.warning(f"Rate limiter record error: {e}")
