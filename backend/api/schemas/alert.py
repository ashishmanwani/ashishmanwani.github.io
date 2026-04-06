import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from api.schemas.product import ProductOut


class AlertCreate(BaseModel):
    product_id: uuid.UUID
    target_price: Decimal
    notify_on_any_drop: bool = False


class AlertUpdate(BaseModel):
    target_price: Decimal | None = None
    is_active: bool | None = None
    notify_on_any_drop: bool | None = None


class AlertOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    target_price: Decimal
    is_active: bool
    notify_on_any_drop: bool
    last_notified_at: datetime | None
    triggered_count: int
    created_at: datetime
    product: ProductOut | None = None

    model_config = {"from_attributes": True}
