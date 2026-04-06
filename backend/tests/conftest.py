"""
Pytest configuration and shared fixtures.
Tests that don't need a real database use mock/in-memory fixtures.
"""

import pytest


@pytest.fixture
def sample_flipkart_html():
    """Load saved Flipkart product HTML fixture."""
    from pathlib import Path
    fixture_path = Path(__file__).parent / "fixtures" / "flipkart_product_page.html"
    if fixture_path.exists():
        return fixture_path.read_text()
    return "<html><body><div class='_30jeq3'>₹74,999</div></body></html>"


@pytest.fixture
def sample_amazon_html():
    """Load saved Amazon product HTML fixture."""
    from pathlib import Path
    fixture_path = Path(__file__).parent / "fixtures" / "amazon_product_page.html"
    if fixture_path.exists():
        return fixture_path.read_text()
    return '<html><body><span class="a-price"><span class="a-offscreen">₹19,990</span></span></body></html>'


@pytest.fixture
def sample_myntra_html():
    """Load saved Myntra product HTML fixture."""
    from pathlib import Path
    fixture_path = Path(__file__).parent / "fixtures" / "myntra_product_page.html"
    if fixture_path.exists():
        return fixture_path.read_text()
    return "<html><body><div class='pdp-price'><strong>₹2,999</strong></div></body></html>"
