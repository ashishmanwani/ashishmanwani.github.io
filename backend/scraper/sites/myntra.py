"""
Myntra scraper — always requires Playwright (full SPA).
Strategy:
  1. Playwright + stealth
  2. Wait for price element (.pdp-price__discounted)
  3. Intercept network XHR responses (more reliable than DOM parsing)
  4. CSS selector fallback on DOM
  5. LLM fallback
"""

import asyncio
import json
import logging
import random
import re

from scraper.base import BaseScraper, ScrapeResult
from scraper.browser import browser_pool, page_actions
from scraper.browser.session_manager import (
    load_cookies,
    playwright_cookies_to_dict,
    save_cookies,
)
from scraper.extractors.css_extractor import CssExtractor
from scraper.extractors.llm_extractor import LlmExtractor
from api.config import settings

logger = logging.getLogger(__name__)

css_extractor = CssExtractor()
llm_extractor = LlmExtractor()

# Myntra's internal product API pattern
MYNTRA_API_PATTERNS = [
    "/api/pdp/fetch/description",
    "/api/pdp/fetch/v2",
    "/api/pdp/v2",
]

PRICE_CLEAN_RE = re.compile(r"[^\d.]")


def _cloudflare_blocked(html: str) -> bool:
    return "cf-browser-verification" in html or "cf_chl_opt" in html


class MyntraScraper(BaseScraper):
    site = "myntra"

    async def scrape(self, url: str, proxy: dict | None = None) -> ScrapeResult:
        proxy_id = self._proxy_id(proxy)
        captured_api_data: dict = {}

        context = await browser_pool.new_context(proxy=proxy)
        try:
            stored_cookies = load_cookies(proxy_id, "myntra")
            if stored_cookies:
                await context.add_cookies(stored_cookies)

            page = await context.new_page()
            await page_actions.block_unnecessary_resources(page)

            # Intercept Myntra's product API responses
            async def handle_response(response):
                if any(pat in response.url for pat in MYNTRA_API_PATTERNS):
                    try:
                        if response.status == 200:
                            body = await response.json()
                            captured_api_data["body"] = body
                            captured_api_data["url"] = response.url
                    except Exception:
                        pass

            page.on("response", handle_response)

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Check for Cloudflare challenge
            html_initial = await page.content()
            if _cloudflare_blocked(html_initial):
                logger.warning(f"Myntra Cloudflare block detected for {url}")
                return ScrapeResult(success=False, is_blocked=True, error="Cloudflare blocked")

            # Wait for price element
            try:
                await page.wait_for_selector(".pdp-price", timeout=15000)
            except Exception:
                logger.debug("Price element not found within timeout, proceeding anyway")

            await page_actions.scroll_naturally(page, steps=2)
            await asyncio.sleep(random.uniform(1, 2))

            # ── Extraction from API ────────────────────────────────────────────
            if captured_api_data:
                price = self._extract_from_api(captured_api_data.get("body", {}))
                if price is not None:
                    from decimal import Decimal
                    return ScrapeResult(
                        success=True,
                        price=Decimal(str(price)),
                        extraction_method="xhr_intercept",
                        confidence=0.97,
                    )

            # ── Extraction from DOM ────────────────────────────────────────────
            html = await page.content()

            # Check out-of-stock
            if "size-buttons-notify-me" in html or "pdp-out-of-stock" in html:
                return ScrapeResult(
                    success=True,
                    is_out_of_stock=True,
                    extraction_method="css_oos",
                    confidence=0.90,
                )

            result = css_extractor.extract(html, "myntra")
            if result.success:
                cookies = await context.cookies()
                save_cookies(proxy_id, "myntra", playwright_cookies_to_dict(cookies))
                return self._make_result(result)

            # LLM fallback
            if settings.ENABLE_LLM_FALLBACK:
                result = llm_extractor.extract(html, "myntra")
                if result.success and result.confidence >= settings.LLM_CONFIDENCE_THRESHOLD:
                    return self._make_result(result)

            return ScrapeResult(success=False, error="All Myntra extraction methods failed")

        finally:
            await context.close()

    def _extract_from_api(self, body: dict) -> float | None:
        """Parse Myntra's product API response for current discounted price."""
        try:
            # Myntra API v2 structure
            style = body.get("style", {})
            prices = style.get("prices", [])
            if prices:
                discounted = prices[0].get("discounted")
                if discounted:
                    return float(discounted)

            # Alternate path
            mrp_str = style.get("mrpFormatted") or body.get("mrpFormatted", "")
            discounted_str = style.get("discountedPriceFormatted") or body.get("discountedPriceFormatted", "")
            target = discounted_str or mrp_str
            if target:
                cleaned = PRICE_CLEAN_RE.sub("", target)
                if cleaned:
                    return float(cleaned)
        except Exception:
            pass
        return None

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
