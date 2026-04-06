"""
ProxyManager — Redis-backed proxy pool with health scoring and rotation.

Redis keys:
  proxy:pool:{site}             ZSET → {proxy_id: composite_score}
  proxy:meta:{proxy_id}         HASH → proxy metadata
  proxy:rate:{proxy_id}:{site}  STRING → request count, TTL=60s
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone

import redis

from api.config import settings
from proxy.models import ProxyModel

logger = logging.getLogger(__name__)

BAN_DURATION_SECONDS = 6 * 60 * 60   # 6 hours
RATE_WINDOW_SECONDS = 60
MAX_FAILS_BEFORE_BAN = 3


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _proxy_id(host: str, port: int, username: str | None) -> str:
    key = f"{host}:{port}:{username or ''}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


class ProxyManager:
    """
    Manages a pool of proxies per site with health-aware rotation.
    Proxies are scored in a Redis sorted set and selected by composite score.
    """

    def get_proxy(self, site: str) -> ProxyModel | None:
        """
        Return the best-scored available proxy for the given site.
        Returns None if no proxies are available (use direct connection).
        """
        r = _get_redis()
        pool_key = f"proxy:pool:{site}"

        # Get top-scored proxies
        candidates = r.zrevrangebyscore(pool_key, "+inf", "-inf", start=0, num=10)
        if not candidates:
            return None

        for proxy_id in candidates:
            proxy = self._load_proxy(r, proxy_id)
            if proxy and not proxy.is_banned:
                return proxy

        return None

    def report_success(self, proxy: ProxyModel | None, site: str, response_ms: float) -> None:
        if proxy is None:
            return
        r = _get_redis()
        meta_key = f"proxy:meta:{proxy.id}"

        # Update stats
        r.hincrby(meta_key, "success_count", 1)
        current_avg = float(r.hget(meta_key, "avg_response_ms") or 0)
        success_count = int(r.hget(meta_key, "success_count") or 1)
        new_avg = (current_avg * (success_count - 1) + response_ms) / success_count
        r.hset(meta_key, "avg_response_ms", new_avg)
        r.hset(meta_key, "last_used_at", datetime.now(tz=timezone.utc).isoformat())

        # Recalculate and update score in the sorted set
        proxy.success_count = success_count
        proxy.avg_response_ms = new_avg
        r.zadd(f"proxy:pool:{site}", {proxy.id: proxy.composite_score()})

    def report_failure(self, proxy: ProxyModel | None, site: str) -> None:
        if proxy is None:
            return
        r = _get_redis()
        meta_key = f"proxy:meta:{proxy.id}"

        fail_count = r.hincrby(meta_key, "fail_count", 1)
        r.hset(meta_key, "last_failed_at", datetime.now(tz=timezone.utc).isoformat())

        if fail_count >= MAX_FAILS_BEFORE_BAN:
            self._ban_proxy(r, proxy, site)
        else:
            proxy.fail_count = fail_count
            r.zadd(f"proxy:pool:{site}", {proxy.id: proxy.composite_score()})

    def report_captcha(self, proxy: ProxyModel | None, site: str) -> None:
        if proxy is None:
            return
        r = _get_redis()
        meta_key = f"proxy:meta:{proxy.id}"

        r.hincrby(meta_key, "captcha_count", 1)
        r.hincrby(meta_key, "fail_count", 1)
        # CAPTCHA = immediately ban (may be IP-level ban)
        self._ban_proxy(r, proxy, site)

    def _ban_proxy(self, r: redis.Redis, proxy: ProxyModel, site: str) -> None:
        meta_key = f"proxy:meta:{proxy.id}"
        banned_until = (
            datetime.now(tz=timezone.utc) + timedelta(seconds=BAN_DURATION_SECONDS)
        ).isoformat()
        r.hset(meta_key, "is_banned", "1")
        r.hset(meta_key, "banned_until", banned_until)
        # Remove from pool sorted set temporarily
        r.zrem(f"proxy:pool:{site}", proxy.id)
        logger.info(f"Proxy {proxy.id} banned for site={site} until {banned_until}")

    def unban_expired(self) -> int:
        """Scan all proxy metadata and unban proxies whose ban has expired. Returns unban count."""
        r = _get_redis()
        now = datetime.now(tz=timezone.utc)
        unbanned = 0

        for key in r.scan_iter("proxy:meta:*"):
            banned = r.hget(key, "is_banned")
            if banned == "1":
                banned_until_str = r.hget(key, "banned_until")
                if banned_until_str:
                    banned_until = datetime.fromisoformat(banned_until_str)
                    if now >= banned_until:
                        r.hset(key, "is_banned", "0")
                        proxy_id = key.split(":")[-1]
                        # Re-add to all site pools
                        for site in ["amazon", "flipkart", "myntra"]:
                            r.zadd(f"proxy:pool:{site}", {proxy_id: 0.5})
                        unbanned += 1

        return unbanned

    def add_proxy(self, host: str, port: int, username: str | None = None,
                  password: str | None = None, protocol: str = "http") -> ProxyModel:
        """Add a new proxy to the pool."""
        r = _get_redis()
        pid = _proxy_id(host, port, username)
        meta_key = f"proxy:meta:{pid}"

        proxy = ProxyModel(
            id=pid, host=host, port=port,
            username=username, password=password, protocol=protocol,
        )

        r.hset(meta_key, mapping={
            "host": host,
            "port": port,
            "username": username or "",
            "password": password or "",
            "protocol": protocol,
            "success_count": 0,
            "fail_count": 0,
            "captcha_count": 0,
            "avg_response_ms": 0,
            "is_banned": "0",
        })

        # Add to all site pools with neutral score
        for site in ["amazon", "flipkart", "myntra"]:
            r.zadd(f"proxy:pool:{site}", {pid: 0.5})

        logger.debug(f"Added proxy {pid} ({host}:{port})")
        return proxy

    def pool_size(self, site: str) -> int:
        r = _get_redis()
        return r.zcard(f"proxy:pool:{site}")

    def _load_proxy(self, r: redis.Redis, proxy_id: str) -> ProxyModel | None:
        meta_key = f"proxy:meta:{proxy_id}"
        data = r.hgetall(meta_key)
        if not data:
            return None

        # Check ban status
        is_banned = data.get("is_banned", "0") == "1"
        banned_until_str = data.get("banned_until", "")
        if is_banned and banned_until_str:
            banned_until = datetime.fromisoformat(banned_until_str)
            if datetime.now(tz=timezone.utc) < banned_until:
                return None  # Still banned
            else:
                # Ban expired — unban inline
                r.hset(meta_key, "is_banned", "0")
                is_banned = False

        return ProxyModel(
            id=proxy_id,
            host=data.get("host", ""),
            port=int(data.get("port", 0)),
            username=data.get("username") or None,
            password=data.get("password") or None,
            protocol=data.get("protocol", "http"),
            success_count=int(data.get("success_count", 0)),
            fail_count=int(data.get("fail_count", 0)),
            captcha_count=int(data.get("captcha_count", 0)),
            avg_response_ms=float(data.get("avg_response_ms", 0)),
            is_banned=is_banned,
        )


# Singleton
proxy_manager = ProxyManager()
