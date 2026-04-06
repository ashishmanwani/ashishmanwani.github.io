import pytest
from api.services.product_service import canonicalize_url, detect_site


def test_detect_amazon():
    assert detect_site("https://www.amazon.in/dp/B08N5WRWNW") == "amazon"


def test_detect_flipkart():
    assert detect_site("https://www.flipkart.com/apple-iphone-15/p/itmfd1d9b4f7c3a2") == "flipkart"


def test_detect_myntra():
    assert detect_site("https://www.myntra.com/shoes/nike/nike-air-max/12345678/buy") == "myntra"


def test_detect_unsupported():
    assert detect_site("https://www.snapdeal.com/product/test") is None


def test_amazon_canonical_extracts_asin():
    url = "https://www.amazon.in/Sony-WH-1000XM5-Cancelling-Headphones/dp/B09XS7JWHH/ref=sr_1_1?keywords=headphones"
    canonical, site = canonicalize_url(url)
    assert site == "amazon"
    assert "/dp/B09XS7JWHH" in canonical
    assert "ref=" not in canonical
    assert "th=1" in canonical
    assert "psc=1" in canonical


def test_flipkart_canonical_keeps_pid():
    url = "https://www.flipkart.com/apple-iphone-15/p/itmfd1d9b4f7c3a2?pid=MOBGTAGPTB3VS24W&otracker=product_breadCrumbs_iPhone+15"
    canonical, site = canonicalize_url(url)
    assert site == "flipkart"
    assert "pid=MOBGTAGPTB3VS24W" in canonical
    assert "otracker=" not in canonical


def test_myntra_canonical_strips_query():
    url = "https://www.myntra.com/shoes/nike/12345678/buy?src=search"
    canonical, site = canonicalize_url(url)
    assert site == "myntra"
    assert "src=" not in canonical
    assert "12345678" in canonical


def test_unsupported_url_raises():
    with pytest.raises(ValueError):
        canonicalize_url("https://www.snapdeal.com/product/test/12345")


def test_url_without_scheme():
    canonical, site = canonicalize_url("www.amazon.in/dp/B09XS7JWHH")
    assert site == "amazon"
    assert canonical.startswith("https://")
