import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_out_of_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Method used: 'json_ld' | 'css_primary' | 'css_secondary' | 'llm_text' | 'llm_vision'
    extraction_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    # Stores: selector_used, response_time_ms, proxy_hash, raw_html_fragment
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="price_records")  # noqa: F821
    notification_logs: Mapped[list["NotificationLog"]] = relationship("NotificationLog", back_populates="price_record")  # noqa: F821
