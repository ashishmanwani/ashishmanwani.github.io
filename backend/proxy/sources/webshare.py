"""
Webshare.io proxy source.
Fetches rotating residential proxies from Webshare API.
Requires WEBSHARE_API_KEY in environment.
"""

import logging

import httpx

from api.config import settings
from proxy.manager import proxy_manager

logger = logging.getLogger(__name__)

WEBSHARE_API_BASE = "https://proxy.webshare.io/api/v2"


def fetch_and_load_proxies(page_size: int = 100) -> int:
    """Fetch proxy list from Webshare and load into pool."""
    if not settings.WEBSHARE_API_KEY:
        logger.warning("WEBSHARE_API_KEY not set, skipping Webshare proxy fetch")
        return 0

    headers = {"Authorization": f"Token {settings.WEBSHARE_API_KEY}"}
    count = 0
    page = 1

    while True:
        try:
            resp = httpx.get(
                f"{WEBSHARE_API_BASE}/proxy/list/",
                headers=headers,
                params={"page": page, "page_size": page_size, "mode": "direct"},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

            for proxy_data in data.get("results", []):
                host = proxy_data.get("proxy_address")
                port = proxy_data.get("port")
                username = proxy_data.get("username")
                password = proxy_data.get("password")

                if host and port:
                    proxy_manager.add_proxy(host, int(port), username, password)
                    count += 1

            # Check if there are more pages
            if not data.get("next"):
                break
            page += 1

        except Exception as e:
            logger.error(f"Failed to fetch Webshare proxies (page {page}): {e}")
            break

    logger.info(f"Loaded {count} proxies from Webshare")
    return count
