from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ExtractionResult:
    price: Decimal | None
    is_out_of_stock: bool = False
    confidence: float = 0.0
    method: str = "unknown"
    title: str | None = None
    image_url: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.price is not None or self.is_out_of_stock


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, html: str, site: str) -> ExtractionResult:
        """Extract price from HTML content."""
        ...
