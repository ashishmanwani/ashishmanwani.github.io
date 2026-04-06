"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-06 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_link_token", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_telegram_link_token", "users", ["telegram_link_token"])

    # ── products ───────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("site", sa.String(20), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scrape_tier", sa.String(10), nullable=False, server_default="normal"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("scrape_config", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_url"),
    )
    op.create_index("ix_products_site", "products", ["site"])
    op.create_index("ix_products_last_scraped_at", "products", ["last_scraped_at"])

    # ── alerts ─────────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_any_drop", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_alert_user_product"),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_product_id", "alerts", ["product_id"])
    op.create_index("ix_alerts_is_active", "alerts", ["is_active"])

    # ── price_records ──────────────────────────────────────────────────────────
    op.create_table(
        "price_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_out_of_stock", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extraction_method", sa.String(30), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_price_records_product_scraped",
        "price_records",
        ["product_id", "scraped_at"],
    )

    # ── scrape_jobs ────────────────────────────────────────────────────────────
    op.create_table(
        "scrape_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="5"),
        sa.Column("attempts", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.SmallInteger(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(64), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scrape_jobs_status", "scrape_jobs", ["status"])
    op.create_index("ix_scrape_jobs_scheduled_at", "scrape_jobs", ["scheduled_at"])

    # ── notification_log ───────────────────────────────────────────────────────
    op.create_table(
        "notification_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price_record_id", sa.BigInteger(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="telegram"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["price_record_id"], ["price_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_log_alert_id", "notification_log", ["alert_id"])


def downgrade() -> None:
    op.drop_table("notification_log")
    op.drop_table("scrape_jobs")
    op.drop_table("price_records")
    op.drop_table("alerts")
    op.drop_table("products")
    op.drop_table("users")
