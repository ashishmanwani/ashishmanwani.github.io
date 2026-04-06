import json
import logging
import re
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

from scraper.extractors.base_extractor import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class JsonLdExtractor(BaseExtractor):
    """
    Extracts price from schema.org JSON-LD embedded in HTML.
    This is Layer 1 — most reliable for Flipkart, sometimes Amazon.
    Confidence: 0.99
    """

    def extract(self, html: str, site: str) -> ExtractionResult:
        soup = BeautifulSoup(html, "lxml")
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            # Handle both single object and array
            items = data if isinstance(data, list) else [data]

            for item in items:
                result = self._parse_item(item)
                if result:
                    return result

        return ExtractionResult(price=None, confidence=0.0, method="json_ld")

    def _parse_item(self, item: dict) -> ExtractionResult | None:
        schema_type = item.get("@type", "")
        if isinstance(schema_type, list):
            schema_type = " ".join(schema_type)

        # Top-level Product or nested via @graph
        if schema_type == "Product" or "Product" in schema_type:
            return self._extract_from_product(item)

        if "@graph" in item:
            for node in item["@graph"]:
                result = self._parse_item(node)
                if result:
                    return result

        return None

    def _extract_from_product(self, item: dict) -> ExtractionResult | None:
        offers = item.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        price_str = offers.get("price") or offers.get("lowPrice")
        if not price_str:
            return None

        try:
            price = Decimal(str(price_str)).quantize(Decimal("0.01"))
        except InvalidOperation:
            # Try stripping currency symbols
            cleaned = re.sub(r"[^\d.]", "", str(price_str))
            try:
                price = Decimal(cleaned).quantize(Decimal("0.01"))
            except InvalidOperation:
                return None

        availability = offers.get("availability", "").lower()
        out_of_stock = "outofstock" in availability or "soldout" in availability

        title = item.get("name")
        image = item.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        if isinstance(image, dict):
            image = image.get("url")

        return ExtractionResult(
            price=price if not out_of_stock else None,
            is_out_of_stock=out_of_stock,
            confidence=0.99,
            method="json_ld",
            title=title,
            image_url=image,
            metadata={"schema_type": "Product", "raw_price": str(price_str)},
        )
