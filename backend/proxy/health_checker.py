"""
Background proxy health checker.
Runs as a Celery maintenance task every 20 minutes.
"""

import logging
import time

import httpx

from proxy.manager import proxy_manager

logger = logging.getLogger(__name__)

TEST_URLS = {
    "amazon": "https://www.amazon.in/robots.txt",
    "flipkart": "https://www.flipkart.com/robots.txt",
    "myntra": "https://www.myntra.com/robots.txt",
}


def check_proxy_health(proxy_id: str, host: str, port: int,
                       username: str | None, password: str | None) -> dict:
    """
    Test a proxy against each site's robots.txt (lightweight, no anti-bot).
    Returns {site: {ok: bool, response_ms: float}}.
    """
    results = {}
    proxy_url = f"http://{host}:{port}"
    if username and password:
        proxy_url = f"http://{username}:{password}@{host}:{port}"

    proxies = {"http://": proxy_url, "https://": proxy_url}

    for site, url in TEST_URLS.items():
        start = time.monotonic()
        try:
            resp = httpx.get(url, proxies=proxies, timeout=10.0, follow_redirects=True)
            elapsed_ms = (time.monotonic() - start) * 1000
            results[site] = {"ok": resp.status_code < 400, "response_ms": elapsed_ms}
        except Exception as e:
            results[site] = {"ok": False, "response_ms": 9999, "error": str(e)}

    return results


def run_health_check_all() -> dict:
    """
    Run health checks for all proxies in the pool.
    Called by the Celery maintenance worker.
    """
    import redis
    from api.config import settings

    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    checked = 0
    failed = 0

    for meta_key in r.scan_iter("proxy:meta:*"):
        proxy_id = meta_key.split(":")[-1]
        data = r.hgetall(meta_key)
        if not data:
            continue

        host = data.get("host", "")
        port = int(data.get("port", 0))
        username = data.get("username") or None
        password = data.get("password") or None

        if not host or not port:
            continue

        results = check_proxy_health(proxy_id, host, port, username, password)
        checked += 1

        for site, result in results.items():
            if result["ok"]:
                proxy_manager.report_success(
                    proxy_manager._load_proxy(r, proxy_id),
                    site,
                    result["response_ms"],
                )
            else:
                proxy_manager.report_failure(
                    proxy_manager._load_proxy(r, proxy_id),
                    site,
                )
                failed += 1

    # Unban expired proxies
    unbanned = proxy_manager.unban_expired()
    logger.info(f"Health check complete: {checked} proxies checked, {failed} failures, {unbanned} unbanned")
    return {"checked": checked, "failed": failed, "unbanned": unbanned}
