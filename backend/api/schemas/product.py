import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, HttpUrl, field_validator


class ProductSubmit(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        supported = ("amazon.in", "flipkart.com", "myntra.com")
        if not any(site in v for site in supported):
            raise ValueError("Only Amazon India, Flipkart, and Myntra URLs are supported.")
        return v


class ProductOut(BaseModel):
    id: uuid.UUID
    canonical_url: str
    site: str
    title: str | None
    image_url: str | None
    current_price: Decimal | None
    currency: str
    last_scraped_at: datetime | None
    scrape_tier: str
    created_at: datetime

    model_config = {"from_attributes": True}
