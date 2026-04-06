from scraper.base import BaseScraper
from scraper.sites.amazon import AmazonScraper
from scraper.sites.flipkart import FlipkartScraper
from scraper.sites.myntra import MyntraScraper

_REGISTRY: dict[str, BaseScraper] = {
    "amazon": AmazonScraper(),
    "flipkart": FlipkartScraper(),
    "myntra": MyntraScraper(),
}


def get_scraper(site: str) -> BaseScraper:
    scraper = _REGISTRY.get(site)
    if not scraper:
        raise ValueError(f"No scraper registered for site: {site}")
    return scraper


def supported_sites() -> list[str]:
    return list(_REGISTRY.keys())
