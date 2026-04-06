"""
HTTP client using curl_cffi for Chrome TLS impersonation.
This defeats TLS fingerprinting (JA3/JA4) — critical for Flipkart and some Amazon requests.
"""

import logging
from dataclasses import dataclass

from curl_cffi import requests as cffi_requests

from scraper.http.headers import get_headers

logger = logging.getLogger(__name__)

IMPERSONATE_VERSION = "chrome124"


@dataclass
class HttpResponse:
    status_code: int
    html: str
    url: str
    is_captcha: bool = False
    is_blocked: bool = False


def _detect_captcha(html: str, url: str) -> bool:
    captcha_signals = [
        "/errors/validateCaptcha" in url,
        "Robot Check" in html,
        "Enter the characters you see below" in html,
        "cf-challenge" in html,
        "cf_chl_opt" in html,
        "Please complete the security check" in html,
        "CAPTCHA" in html and "amazon" in url.lower(),
    ]
    return any(captcha_signals)


def _detect_blocked(status_code: int, html: str) -> bool:
    if status_code in (403, 503, 429):
        return True
    if "Access Denied" in html and status_code == 403:
        return True
    return False


def fetch(
    url: str,
    site: str,
    proxy: dict | None = None,
    timeout: int = 20,
    cookies: dict | None = None,
) -> HttpResponse:
    """
    Fetch a URL using curl_cffi with Chrome TLS impersonation.

    proxy format: {"http": "http://user:pass@host:port", "https": "http://user:pass@host:port"}
    """
    headers = get_headers(site)

    try:
        response = cffi_requests.get(
            url,
            headers=headers,
            impersonate=IMPERSONATE_VERSION,
            proxies=proxy,
            cookies=cookies or {},
            timeout=timeout,
            allow_redirects=True,
        )

        html = response.text
        final_url = str(response.url)
        is_captcha = _detect_captcha(html, final_url)
        is_blocked = _detect_blocked(response.status_code, html)

        if is_captcha:
            logger.warning(f"CAPTCHA detected for {url}")
        elif is_blocked:
            logger.warning(f"Blocked (HTTP {response.status_code}) for {url}")

        return HttpResponse(
            status_code=response.status_code,
            html=html,
            url=final_url,
            is_captcha=is_captcha,
            is_blocked=is_blocked,
        )

    except Exception as e:
        logger.error(f"HTTP fetch failed for {url}: {e}")
        return HttpResponse(
            status_code=0,
            html="",
            url=url,
            is_captcha=False,
            is_blocked=True,
        )
