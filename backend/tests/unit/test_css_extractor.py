import pytest
from decimal import Decimal

from scraper.extractors.css_extractor import CssExtractor, parse_price

extractor = CssExtractor()

AMAZON_HTML = """
<html><body>
<div id="price_block">
  <span class="a-price">
    <span class="a-offscreen">₹19,990</span>
    <span class="a-price-whole">19,990</span>
  </span>
</div>
</body></html>
"""

FLIPKART_HTML = """
<html><body>
<div class="CEmiEU">
  <div class="_30jeq3 _16Jk6d">₹74,999</div>
</div>
</body></html>
"""

FLIPKART_HTML_OOS = """
<html><body>
<div class="_16FRp0">
  <span>Notify Me</span>
</div>
</body></html>
"""

AMAZON_EMI_HTML = """
<html><body>
<span class="a-price a-text-price"><span class="a-offscreen">₹500</span></span>
<span>No Cost EMI ₹500/month</span>
<span class="a-price"><span class="a-offscreen">₹19,990</span></span>
</body></html>
"""


class TestParsePrice:
    def test_basic_price(self):
        assert parse_price("₹19,990") == Decimal("19990.00")

    def test_price_with_rs(self):
        assert parse_price("Rs.1,299") == Decimal("1299.00")

    def test_price_with_spaces(self):
        assert parse_price("  ₹ 5,999  ") == Decimal("5999.00")

    def test_skip_emi_price(self):
        assert parse_price("₹500/month EMI") is None

    def test_skip_no_cost_emi(self):
        assert parse_price("No Cost EMI ₹500") is None

    def test_returns_none_for_empty(self):
        assert parse_price("") is None

    def test_returns_none_for_non_numeric(self):
        assert parse_price("Out of Stock") is None


class TestCssExtractor:
    def test_amazon_extracts_price(self):
        result = extractor.extract(AMAZON_HTML, "amazon")
        assert result.success
        assert result.price == Decimal("19990.00")
        assert result.method in ("css_primary", "css_secondary")

    def test_flipkart_extracts_price(self):
        result = extractor.extract(FLIPKART_HTML, "flipkart")
        assert result.success
        assert result.price == Decimal("74999.00")

    def test_unsupported_site_returns_empty(self):
        result = extractor.extract("<html></html>", "snapdeal")
        assert not result.success

    def test_empty_html_returns_empty(self):
        result = extractor.extract("", "amazon")
        assert not result.success
