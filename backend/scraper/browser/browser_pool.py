"""
Playwright browser instance pool.
Creates one browser process per worker and uses contexts (tabs) per scrape.
This is memory-efficient — each context is isolated, browser is shared.
"""

import logging

from playwright.async_api import Browser, Playwright, async_playwright

from scraper.browser.stealth import get_random_viewport, get_stealth_script
from scraper.http.headers import CHROME_USER_AGENTS

logger = logging.getLogger(__name__)

_playwright: Playwright | None = None
_browser: Browser | None = None

import random


async def get_browser() -> Browser:
    """Get or create the shared browser instance."""
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        logger.info("Browser launched")
    return _browser


async def close_browser() -> None:
    """Gracefully close the browser and Playwright."""
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


async def new_context(proxy: dict | None = None):
    """
    Create a new isolated browser context with stealth patches applied.
    Returns a Playwright BrowserContext.
    """
    browser = await get_browser()
    viewport = get_random_viewport()
    ua = random.choice(CHROME_USER_AGENTS)

    context_kwargs = {
        "viewport": viewport,
        "user_agent": ua,
        "locale": "en-IN",
        "timezone_id": "Asia/Kolkata",
        "extra_http_headers": {
            "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        "java_script_enabled": True,
        "ignore_https_errors": False,
    }

    if proxy:
        proxy_url = proxy.get("https") or proxy.get("http", "")
        if proxy_url:
            # Parse proxy URL for Playwright format
            import re
            match = re.match(r"https?://(?:(.+):(.+)@)?(.+):(\d+)", proxy_url)
            if match:
                user, password, server, port = match.groups()
                context_kwargs["proxy"] = {
                    "server": f"http://{server}:{port}",
                    **({"username": user, "password": password} if user else {}),
                }

    context = await browser.new_context(**context_kwargs)

    # Inject stealth patches into every new page in this context
    await context.add_init_script(get_stealth_script())

    return context
