"""
Free proxy list scraper — LOW QUALITY, use only as last resort.
Scrapes public proxy lists and loads usable ones into the pool.
Expect 60-80% of these to be dead or blocked.
"""

import logging
import re

import httpx

from proxy.manager import proxy_manager

logger = logging.getLogger(__name__)

FREE_PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
]

PROXY_LINE_RE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})$")


def fetch_free_proxies() -> int:
    """Fetch free proxy lists and load into pool. Returns count loaded."""
    count = 0
    for url in FREE_PROXY_SOURCES:
        try:
            resp = httpx.get(url, timeout=15.0)
            for line in resp.text.splitlines():
                line = line.strip()
                match = PROXY_LINE_RE.match(line)
                if match:
                    host, port = match.groups()
                    proxy_manager.add_proxy(host, int(port))
                    count += 1
        except Exception as e:
            logger.warning(f"Failed to fetch proxy list from {url}: {e}")

    logger.info(f"Loaded {count} free proxies (expect high churn rate)")
    return count
