"""
Amazon India scraper — THE HARDEST FILE in the codebase.
Amazon uses PerimeterX, TLS fingerprinting, behavioral analysis, and CAPTCHA.

Strategy:
  1. Playwright with full stealth patches
  2. Session warming: homepage → category → product (3-step browsing)
  3. Amazon-specific cookies (i18n-prefs=INR, lc-acbin=en_IN)
  4. Multi-selector fallback chain
  5. LLM fallback on extraction failure
  6. CAPTCHA detection → proxy rotation → retry
"""

import asyncio
import logging
import random

from scraper.base import BaseScraper, ScrapeResult
from scraper.browser import browser_pool, page_actions
from scraper.browser.session_manager import (
    clear_cookies,
    load_cookies,
    playwright_cookies_to_dict,
    save_cookies,
)
from scraper.extractors.css_extractor import CssExtractor
from scraper.extractors.json_ld_extractor import JsonLdExtractor
from scraper.extractors.llm_extractor import LlmExtractor, LlmVisionExtractor
from scraper.extractors.selector_configs import AMAZON_PRICE_SELECTORS
from api.config import settings

logger = logging.getLogger(__name__)

json_ld_extractor = JsonLdExtractor()
css_extractor = CssExtractor()
llm_extractor = LlmExtractor()
vision_extractor = LlmVisionExtractor()

# Amazon India warming URLs
AMAZON_HOME = "https://www.amazon.in"
AMAZON_CATEGORY_URLS = [
    "https://www.amazon.in/s?k=electronics",
    "https://www.amazon.in/s?k=mobile+phones",
    "https://www.amazon.in/gp/bestsellers/electronics",
    "https://www.amazon.in/s?k=laptop",
]

# Required cookies for INR pricing
AMAZON_REQUIRED_COOKIES = [
    {"name": "i18n-prefs", "value": "INR", "domain": ".amazon.in", "path": "/"},
    {"name": "lc-acbin", "value": "en_IN", "domain": ".amazon.in", "path": "/"},
    {"name": "sp-cdn", "value": "L5Z9:IN", "domain": ".amazon.in", "path": "/"},
]


def _detect_amazon_captcha(html: str, url: str) -> bool:
    return (
        "/errors/validateCaptcha" in url
        or "Robot Check" in html
        or "Enter the characters you see below" in html
        or "Type the characters you see in this image" in html
    )


class AmazonScraper(BaseScraper):
    site = "amazon"

    async def scrape(self, url: str, proxy: dict | None = None) -> ScrapeResult:
        proxy_id = self._proxy_id(proxy)
        max_attempts = 2

        for attempt in range(max_attempts):
            try:
                result = await self._scrape_attempt(url, proxy, proxy_id)
                if result.is_captcha:
                    logger.warning(f"Amazon CAPTCHA on attempt {attempt + 1}, clearing session")
                    clear_cookies(proxy_id, "amazon")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(random.uniform(5, 15))
                        continue
                return result
            except Exception as e:
                logger.error(f"Amazon scrape attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    return ScrapeResult(success=False, error=str(e))

        return ScrapeResult(success=False, error="Max CAPTCHA retries exceeded")

    async def _scrape_attempt(
        self, url: str, proxy: dict | None, proxy_id: str
    ) -> ScrapeResult:
        context = await browser_pool.new_context(proxy=proxy)
        try:
            # Load stored cookies
            stored_cookies = load_cookies(proxy_id, "amazon")
            if stored_cookies:
                await context.add_cookies(stored_cookies)
            else:
                # Fresh session — inject required cookies pre-emptively
                await context.add_cookies(AMAZON_REQUIRED_COOKIES)

            page = await context.new_page()
            await page_actions.block_unnecessary_resources(page)

            # Session warming for fresh sessions (no stored cookies)
            if not stored_cookies:
                warmed = await self._warm_session(page)
                if not warmed:
                    logger.warning("Session warming failed, proceeding anyway")

            # Rate limit delay
            await asyncio.sleep(random.uniform(2, 5))

            # Navigate to product page
            logger.debug(f"Loading Amazon product: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Check for CAPTCHA immediately
            current_url = page.url
            html = await page.content()
            if _detect_amazon_captcha(html, current_url):
                return ScrapeResult(success=False, is_captcha=True, error="CAPTCHA detected")

            # Human-like interaction
            await page_actions.random_mouse_move(page)
            await page_actions.scroll_naturally(page, steps=2)
            await asyncio.sleep(random.uniform(1, 3))

            # Re-check HTML after interaction (dynamic content)
            html = await page.content()

            # ── Extraction chain ────────────────────────────────────────────
            # Layer 1: JSON-LD
            result = json_ld_extractor.extract(html, "amazon")
            if result.success and result.confidence >= 0.90:
                await self._save_session(context, proxy_id)
                return self._make_result(result)

            # Layer 2+3: CSS selectors
            result = css_extractor.extract(html, "amazon")
            if result.success and result.confidence >= 0.75:
                await self._save_session(context, proxy_id)
                return self._make_result(result)

            # Layer 4: LLM text extraction
            if settings.ENABLE_LLM_FALLBACK:
                result = llm_extractor.extract(html, "amazon")
                if result.success and result.confidence >= settings.LLM_CONFIDENCE_THRESHOLD:
                    await self._save_session(context, proxy_id)
                    return self._make_result(result)

            # Layer 5: Vision LLM (screenshot-based)
            if settings.ENABLE_VISION_FALLBACK:
                screenshot = await page.screenshot(type="png", clip={
                    "x": page.viewport_size["width"] // 2,
                    "y": 0,
                    "width": page.viewport_size["width"] // 2,
                    "height": min(600, page.viewport_size["height"]),
                })
                result_vision = vision_extractor.extract_from_screenshot(screenshot, "amazon")
                if result_vision.success:
                    await self._save_session(context, proxy_id)
                    return self._make_result(result_vision)

            await self._save_session(context, proxy_id)
            return ScrapeResult(success=False, error="All extraction layers failed")

        finally:
            await context.close()

    async def _warm_session(self, page) -> bool:
        """
        3-step session warming to build a browsing history before hitting product.
        Amazon's bot detection checks browsing patterns.
        """
        try:
            # Step 1: Homepage
            await page.goto(AMAZON_HOME, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(random.uniform(1.5, 3.0))
            await page_actions.scroll_naturally(page, steps=2, delay_range=(0.3, 0.8))

            # Step 2: Category page
            category_url = random.choice(AMAZON_CATEGORY_URLS)
            await page.goto(category_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(random.uniform(1.0, 2.5))
            await page_actions.random_mouse_move(page)

            logger.debug("Amazon session warmed successfully")
            return True
        except Exception as e:
            logger.warning(f"Session warming failed: {e}")
            return False

    async def _save_session(self, context, proxy_id: str) -> None:
        try:
            cookies = await context.cookies()
            save_cookies(proxy_id, "amazon", playwright_cookies_to_dict(cookies))
        except Exception as e:
            logger.warning(f"Failed to save Amazon session: {e}")

    def _make_result(self, extraction_result) -> ScrapeResult:
        return ScrapeResult(
            success=extraction_result.success,
            price=extraction_result.price,
            title=extraction_result.title,
            image_url=extraction_result.image_url,
            is_out_of_stock=extraction_result.is_out_of_stock,
            extraction_method=extraction_result.method,
            confidence=extraction_result.confidence,
            metadata=extraction_result.metadata,
        )

    def _proxy_id(self, proxy: dict | None) -> str:
        if proxy is None:
            return "direct"
        host = proxy.get("https", proxy.get("http", ""))
        import hashlib
        return hashlib.md5(host.encode()).hexdigest()[:8]
