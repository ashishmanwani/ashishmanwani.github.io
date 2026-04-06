from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ScrapeResult:
    success: bool
    price: Decimal | None = None
    title: str | None = None
    image_url: str | None = None
    is_out_of_stock: bool = False
    extraction_method: str = "unknown"
    confidence: float = 0.0
    is_captcha: bool = False
    is_blocked: bool = False
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class BaseScraper(ABC):
    site: str = ""

    @abstractmethod
    async def scrape(self, url: str, proxy: dict | None = None) -> ScrapeResult:
        """
        Scrape the product page and return a ScrapeResult.
        proxy format: {"http": "...", "https": "..."} or None for direct connection.
        """
        ...

    def _make_proxy_dict(self, proxy_model) -> dict | None:
        """Convert a proxy model to the dict format expected by HTTP clients."""
        if proxy_model is None:
            return None
        proxy_url = f"http://{proxy_model.host}:{proxy_model.port}"
        if proxy_model.username and proxy_model.password:
            proxy_url = f"http://{proxy_model.username}:{proxy_model.password}@{proxy_model.host}:{proxy_model.port}"
        return {"http": proxy_url, "https": proxy_url}
