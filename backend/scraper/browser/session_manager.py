"""
Per-proxy cookie jar persistence using Redis.
Keeps warm sessions alive between scrapes to reduce CAPTCHA triggers.
"""

import json
import logging
from datetime import timedelta

import redis

from api.config import settings

logger = logging.getLogger(__name__)

COOKIE_TTL = int(timedelta(hours=4).total_seconds())


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def save_cookies(proxy_id: str, site: str, cookies: list[dict]) -> None:
    """Serialize and store cookies for a proxy+site combination."""
    try:
        r = _get_redis()
        key = f"proxy:cookies:{proxy_id}:{site}"
        r.setex(key, COOKIE_TTL, json.dumps(cookies))
    except Exception as e:
        logger.warning(f"Failed to save cookies for proxy {proxy_id}: {e}")


def load_cookies(proxy_id: str, site: str) -> list[dict]:
    """Load stored cookies for a proxy+site combination."""
    try:
        r = _get_redis()
        key = f"proxy:cookies:{proxy_id}:{site}"
        data = r.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Failed to load cookies for proxy {proxy_id}: {e}")
    return []


def clear_cookies(proxy_id: str, site: str) -> None:
    """Clear cookies after CAPTCHA or ban — force fresh session."""
    try:
        r = _get_redis()
        r.delete(f"proxy:cookies:{proxy_id}:{site}")
    except Exception as e:
        logger.warning(f"Failed to clear cookies for proxy {proxy_id}: {e}")


def playwright_cookies_to_dict(cookies: list) -> list[dict]:
    """Convert Playwright cookie objects to plain dicts for serialization."""
    return [
        {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
            "sameSite": c.get("sameSite", "None"),
        }
        for c in cookies
    ]
