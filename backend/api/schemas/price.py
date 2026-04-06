import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PriceRecordOut(BaseModel):
    id: int
    product_id: uuid.UUID
    price: Decimal | None
    is_out_of_stock: bool
    extraction_method: str | None
    confidence: Decimal | None
    scraped_at: datetime

    model_config = {"from_attributes": True}


class PriceHistoryOut(BaseModel):
    product_id: uuid.UUID
    records: list[PriceRecordOut]
    total: int
