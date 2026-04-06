import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Canonical URL — deduplicated. Multiple users tracking same URL share one row.
    canonical_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    site: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    # Tier: 'critical' | 'high' | 'normal' | 'low'
    scrape_tier: Mapped[str] = mapped_column(String(10), nullable=False, default="normal")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Site-specific hints: variant selectors, default variant, etc.
    scrape_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="product", cascade="all, delete-orphan")  # noqa: F821
    price_records: Mapped[list["PriceRecord"]] = relationship("PriceRecord", back_populates="product", cascade="all, delete-orphan")  # noqa: F821
    scrape_jobs: Mapped[list["ScrapeJob"]] = relationship("ScrapeJob", back_populates="product", cascade="all, delete-orphan")  # noqa: F821
