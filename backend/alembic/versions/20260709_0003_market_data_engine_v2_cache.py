"""market data engine v2 cache

Revision ID: 20260709_0003
Revises: 20260709_0002
Create Date: 2026-07-09 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260709_0003"
down_revision = "20260709_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_cache",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("cache_key", sa.String(length=240), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("data_type", sa.String(length=40), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("quality_score", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_market_data_cache_cache_key"), "market_data_cache", ["cache_key"], unique=True)
    op.create_index(op.f("ix_market_data_cache_data_type"), "market_data_cache", ["data_type"], unique=False)
    op.create_index(op.f("ix_market_data_cache_expires_at"), "market_data_cache", ["expires_at"], unique=False)
    op.create_index(op.f("ix_market_data_cache_provider"), "market_data_cache", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_market_data_cache_provider"), table_name="market_data_cache")
    op.drop_index(op.f("ix_market_data_cache_expires_at"), table_name="market_data_cache")
    op.drop_index(op.f("ix_market_data_cache_data_type"), table_name="market_data_cache")
    op.drop_index(op.f("ix_market_data_cache_cache_key"), table_name="market_data_cache")
    op.drop_table("market_data_cache")
