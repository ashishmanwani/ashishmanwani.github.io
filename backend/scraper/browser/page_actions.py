"""
Playwright page helper actions for human-like interaction.
"""

import asyncio
import logging
import random

logger = logging.getLogger(__name__)


async def scroll_naturally(page, steps: int = 3, delay_range: tuple = (0.5, 1.5)) -> None:
    """Simulate natural scrolling behavior to trigger lazy-loaded content."""
    viewport_height = page.viewport_size["height"]
    for i in range(steps):
        scroll_amount = random.randint(300, viewport_height)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(*delay_range))
    # Scroll back up slightly (natural behavior)
    await page.evaluate("window.scrollBy(0, -200)")
    await asyncio.sleep(random.uniform(0.3, 0.8))


async def wait_for_price(page, selectors: list[str], timeout: int = 15000) -> str | None:
    """
    Wait for any of the price selectors to appear.
    Returns the first matching element's text, or None on timeout.
    """
    for selector, _ in selectors:
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            el = await page.query_selector(selector)
            if el:
                text = await el.inner_text()
                if text and "₹" in text or any(c.isdigit() for c in text):
                    return text.strip()
        except Exception:
            continue
    return None


async def block_unnecessary_resources(page) -> None:
    """
    Block images, fonts, and analytics to reduce bandwidth.
    Images/fonts are not needed for price extraction.
    """
    blocked_types = {"image", "font", "media"}
    blocked_domains = {
        "google-analytics.com", "googletagmanager.com", "doubleclick.net",
        "facebook.net", "amazon-adsystem.com", "bat.bing.com",
        "analytics.myntra.com", "log.flipkart.com",
    }

    async def handle_route(route):
        resource_type = route.request.resource_type
        url = route.request.url

        if resource_type in blocked_types:
            await route.abort()
            return

        if any(domain in url for domain in blocked_domains):
            await route.abort()
            return

        await route.continue_()

    await page.route("**/*", handle_route)


async def random_mouse_move(page) -> None:
    """Simulate random mouse movement for anti-bot evasion."""
    viewport = page.viewport_size
    if not viewport:
        return
    x = random.randint(100, viewport["width"] - 100)
    y = random.randint(100, viewport["height"] - 100)
    await page.mouse.move(x, y)
    await asyncio.sleep(random.uniform(0.1, 0.3))
