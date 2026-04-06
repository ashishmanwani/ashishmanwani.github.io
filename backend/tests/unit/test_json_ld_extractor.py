import pytest
from decimal import Decimal

from scraper.extractors.json_ld_extractor import JsonLdExtractor

extractor = JsonLdExtractor()

FLIPKART_HTML_WITH_JSON_LD = """
<html>
<head>
<script type="application/ld+json">
{
  "@context": "http://schema.org",
  "@type": "Product",
  "name": "Apple iPhone 15 (128 GB) - Black",
  "image": "https://rukminim2.flixcart.com/image/iphone15.jpg",
  "offers": {
    "@type": "Offer",
    "price": "69999",
    "priceCurrency": "INR",
    "availability": "http://schema.org/InStock"
  }
}
</script>
</head>
<body><p>Product page</p></body>
</html>
"""

JSON_LD_OUT_OF_STOCK = """
<html>
<head>
<script type="application/ld+json">
{
  "@type": "Product",
  "name": "Test Product",
  "offers": {
    "price": "999",
    "availability": "http://schema.org/OutOfStock"
  }
}
</script>
</head>
</html>
"""

JSON_LD_NO_PRICE = """
<html>
<head>
<script type="application/ld+json">
{
  "@type": "Organization",
  "name": "Flipkart"
}
</script>
</head>
</html>
"""

JSON_LD_ARRAY = """
<html>
<head>
<script type="application/ld+json">
[
  {"@type": "WebSite", "name": "Flipkart"},
  {
    "@type": "Product",
    "name": "Samsung Galaxy S24",
    "offers": {"price": "74999", "availability": "http://schema.org/InStock"}
  }
]
</script>
</head>
</html>
"""


def test_extracts_price_from_flipkart_json_ld():
    result = extractor.extract(FLIPKART_HTML_WITH_JSON_LD, "flipkart")
    assert result.success
    assert result.price == Decimal("69999.00")
    assert result.confidence == 0.99
    assert result.method == "json_ld"
    assert result.title == "Apple iPhone 15 (128 GB) - Black"


def test_detects_out_of_stock():
    result = extractor.extract(JSON_LD_OUT_OF_STOCK, "flipkart")
    assert result.is_out_of_stock
    assert result.price is None
    assert result.confidence == 0.99


def test_returns_empty_when_no_product_schema():
    result = extractor.extract(JSON_LD_NO_PRICE, "flipkart")
    assert not result.success
    assert result.price is None


def test_handles_array_json_ld():
    result = extractor.extract(JSON_LD_ARRAY, "flipkart")
    assert result.success
    assert result.price == Decimal("74999.00")


def test_handles_malformed_json():
    html = '<script type="application/ld+json">{invalid json</script>'
    result = extractor.extract(html, "flipkart")
    assert not result.success
