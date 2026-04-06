import logging
import re
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

from scraper.extractors.base_extractor import BaseExtractor, ExtractionResult
from scraper.extractors.selector_configs import (
    AMAZON_IMAGE_SELECTORS,
    AMAZON_OUT_OF_STOCK_SELECTORS,
    AMAZON_PRICE_SELECTORS,
    AMAZON_TITLE_SELECTORS,
    FLIPKART_OUT_OF_STOCK_SELECTORS,
    FLIPKART_PRICE_SELECTORS,
    FLIPKART_TITLE_SELECTORS,
    MYNTRA_OUT_OF_STOCK_SELECTORS,
    MYNTRA_PRICE_SELECTORS,
    MYNTRA_TITLE_SELECTORS,
)

logger = logging.getLogger(__name__)

SITE_CONFIG = {
    "amazon": {
        "price": AMAZON_PRICE_SELECTORS,
        "oos": AMAZON_OUT_OF_STOCK_SELECTORS,
        "title": AMAZON_TITLE_SELECTORS,
        "image": AMAZON_IMAGE_SELECTORS,
    },
    "flipkart": {
        "price": FLIPKART_PRICE_SELECTORS,
        "oos": FLIPKART_OUT_OF_STOCK_SELECTORS,
        "title": FLIPKART_TITLE_SELECTORS,
        "image": [],
    },
    "myntra": {
        "price": MYNTRA_PRICE_SELECTORS,
        "oos": MYNTRA_OUT_OF_STOCK_SELECTORS,
        "title": MYNTRA_TITLE_SELECTORS,
        "image": [],
    },
}

# Patterns to SKIP (EMI, bank offers, original crossed-out prices)
SKIP_PATTERNS = re.compile(
    r"(per\s*month|/month|emi|no\s*cost|bank\s*offer|cashback|extra\s*\d+\s*off)",
    re.IGNORECASE,
)

PRICE_CLEAN_RE = re.compile(r"[^\d.]")


def parse_price(text: str) -> Decimal | None:
    if not text:
        return None
    # Check for skip patterns in parent context
    if SKIP_PATTERNS.search(text):
        return None
    # Strip currency symbols (₹, Rs., INR) and formatting
    cleaned = PRICE_CLEAN_RE.sub("", text.strip())
    # Remove trailing dots from e.g. "1,299."
    cleaned = cleaned.rstrip(".")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


class CssExtractor(BaseExtractor):
    """
    CSS selector-based price extractor.
    Layer 2 (primary selectors) and Layer 3 (secondary selectors).
    """

    def extract(self, html: str, site: str) -> ExtractionResult:
        config = SITE_CONFIG.get(site)
        if not config:
            return ExtractionResult(price=None, confidence=0.0, method="css")

        soup = BeautifulSoup(html, "lxml")

        # Check out-of-stock first
        for oos_selector in config["oos"]:
            el = soup.select_one(oos_selector)
            if el:
                text = el.get_text(strip=True).lower()
                if any(kw in text for kw in ["out of stock", "notify me", "sold out", "currently unavailable"]):
                    return ExtractionResult(
                        price=None,
                        is_out_of_stock=True,
                        confidence=0.95,
                        method="css_oos",
                        metadata={"oos_selector": oos_selector},
                    )

        # Try price selectors in priority order
        for selector, confidence in config["price"]:
            elements = soup.select(selector)
            for el in elements:
                # Skip if parent element contains EMI/bank offer text
                parent_text = el.parent.get_text(" ", strip=True) if el.parent else ""
                if SKIP_PATTERNS.search(parent_text):
                    continue

                text = el.get_text(strip=True)
                price = parse_price(text)
                if price and price > Decimal("0"):
                    title = self._extract_title(soup, config)
                    image = self._extract_image(soup, config)
                    return ExtractionResult(
                        price=price,
                        confidence=confidence,
                        method="css_primary" if confidence >= 0.85 else "css_secondary",
                        title=title,
                        image_url=image,
                        metadata={"selector": selector, "raw_text": text},
                    )

        return ExtractionResult(price=None, confidence=0.0, method="css")

    def _extract_title(self, soup: BeautifulSoup, config: dict) -> str | None:
        for selector in config.get("title", []):
            el = soup.select_one(selector)
            if el:
                return el.get_text(strip=True)
        return None

    def _extract_image(self, soup: BeautifulSoup, config: dict) -> str | None:
        for selector in config.get("image", []):
            el = soup.select_one(selector)
            if el:
                return el.get("src") or el.get("data-src")
        return None
