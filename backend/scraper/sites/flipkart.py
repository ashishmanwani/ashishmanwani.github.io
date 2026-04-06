"""
Flipkart scraper.
Strategy:
  1. HTTP-only with curl_cffi (fast, ~20kB response)
  2. Try JSON-LD extraction (confidence 0.99) — Flipkart includes schema.org for SEO
  3. Try CSS selectors on the HTML
  4. Fallback: Playwright + intercept internal pricing XHR
  5. LLM fallback if all above fail
"""

import asyncio
import json
import logging

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
from scraper.extractors.llm_extractor import LlmExtractor
from scraper.http.client import fetch

logger = logging.getLogger(__name__)

json_ld_extractor = JsonLdExtractor()
css_extractor = CssExtractor()
llm_extractor = LlmExtractor()

# Flipkart internal pricing API URL pattern (intercepted via XHR)
FLIPKART_API_PATTERN = "/api/2/page/fetch"


class FlipkartScraper(BaseScraper):
    site = "flipkart"

    async def scrape(self, url: str, proxy: dict | None = None) -> ScrapeResult:
        proxy_id = self._proxy_id(proxy)

        # ── Layer 1+2: HTTP-only + JSON-LD ────────────────────────────────────
        resp = fetch(url, "flipkart", proxy=proxy)

        if resp.is_captcha or resp.is_blocked:
            logger.warning(f"Flipkart blocked on HTTP path: {url}")
        elif resp.status_code == 200:
            # Try JSON-LD first
            result = json_ld_extractor.extract(resp.html, "flipkart")
            if result.success and result.confidence >= 0.85:
                return self._make_result(result)

            # Try CSS selectors
            result = css_extractor.extract(resp.html, "flipkart")
            if result.success and result.confidence >= 0.80:
                return self._make_result(result)

        # ── Layer 3: Playwright + XHR interception ────────────────────────────
        try:
            return await self._scrape_with_browser(url, proxy, proxy_id)
        except Exception as e:
            logger.error(f"Flipkart browser scrape failed: {e}")
            return ScrapeResult(success=False, error=str(e))

    async def _scrape_with_browser(
        self, url: str, proxy: dict | None, proxy_id: str
    ) -> ScrapeResult:
        captured_price_data = {}

        context = await browser_pool.new_context(proxy=proxy)
        try:
            # Load saved cookies
            stored_cookies = load_cookies(proxy_id, "flipkart")
            if stored_cookies:
                await context.add_cookies(stored_cookies)

            page = await context.new_page()
            await page_actions.block_unnecessary_resources(page)

            # Intercept Flipkart's internal pricing API
            async def handle_response(response):
                if FLIPKART_API_PATTERN in response.url and response.status == 200:
                    try:
                        body = await response.json()
                        captured_price_data["body"] = body
                    except Exception:
                        pass

            page.on("response", handle_response)

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page_actions.scroll_naturally(page)
            await asyncio.sleep(2)

            # Try to extract from intercepted XHR data first
            if captured_price_data:
                price = self._extract_from_xhr(captured_price_data.get("body", {}))
                if price:
                    from decimal import Decimal
                    return ScrapeResult(
                        success=True,
                        price=Decimal(str(price)),
                        extraction_method="xhr_intercept",
                        confidence=0.95,
                    )

            # Otherwise extract from DOM
            html = await page.content()
            result = json_ld_extractor.extract(html, "flipkart")
            if result.success:
                return self._make_result(result)

            result = css_extractor.extract(html, "flipkart")
            if result.success:
                return self._make_result(result)

            # LLM fallback
            result = llm_extractor.extract(html, "flipkart")
            if result.success:
                return self._make_result(result)

            # Save cookies for next session
            cookies = await context.cookies()
            save_cookies(proxy_id, "flipkart", playwright_cookies_to_dict(cookies))

            return ScrapeResult(success=False, error="All extraction methods failed")

        finally:
            await context.close()

    def _extract_from_xhr(self, body: dict) -> float | None:
        """Parse Flipkart's internal API response for price."""
        try:
            slots = body.get("RESPONSE", {}).get("slots", [])
            for slot in slots:
                widget = slot.get("widget", {})
                data = widget.get("data", {})
                # Traverse known price paths in Flipkart's API response
                pricing = (
                    data.get("pricing")
                    or data.get("productInfo", {}).get("value", {}).get("pricing")
                    or {}
                )
                final_price = pricing.get("finalPrice", {}).get("value")
                if final_price:
                    return float(final_price)
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
