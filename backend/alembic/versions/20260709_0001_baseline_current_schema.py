"""baseline current schema

Revision ID: 20260709_0001
Revises:
Create Date: 2026-07-09 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260709_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("ticker", sa.String(length=24), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("asset_class", sa.String(length=40), nullable=False),
        sa.Column("sector", sa.String(length=120), nullable=False),
        sa.Column("segment", sa.String(length=120), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("provider_symbol", sa.String(length=48), nullable=False),
        sa.Column("last_price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_asset_class"), "assets", ["asset_class"], unique=False)
    op.create_index(op.f("ix_assets_sector"), "assets", ["sector"], unique=False)
    op.create_index(op.f("ix_assets_ticker"), "assets", ["ticker"], unique=True)

    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=True),
        sa.Column("type", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_user_id"), "alerts", ["user_id"], unique=False)

    op.create_table(
        "alpha_events",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=True),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("origin", sa.String(length=140), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alpha_events_asset_id"), "alpha_events", ["asset_id"], unique=False)
    op.create_index(op.f("ix_alpha_events_category"), "alpha_events", ["category"], unique=False)
    op.create_index(op.f("ix_alpha_events_occurred_at"), "alpha_events", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_alpha_events_origin"), "alpha_events", ["origin"], unique=False)
    op.create_index(op.f("ix_alpha_events_severity"), "alpha_events", ["severity"], unique=False)
    op.create_index(op.f("ix_alpha_events_status"), "alpha_events", ["status"], unique=False)
    op.create_index(op.f("ix_alpha_events_type"), "alpha_events", ["type"], unique=False)
    op.create_index(op.f("ix_alpha_events_user_id"), "alpha_events", ["user_id"], unique=False)

    op.create_table(
        "dividends",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount_per_share", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("source", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dividends_asset_id"), "dividends", ["asset_id"], unique=False)
    op.create_index(op.f("ix_dividends_user_id"), "dividends", ["user_id"], unique=False)

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("dividend_yield", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("payout", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("revenue_growth", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("profit_growth", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("net_margin", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("roe", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("roic", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("debt_to_ebitda", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("historical_appreciation", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("dividend_consistency", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("payment_frequency", sa.Integer(), nullable=False),
        sa.Column("recurring_profit", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("sector_stability", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("pe_ratio", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("pvp", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id"),
    )

    op.create_table(
        "target_allocations",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("level", sa.String(length=24), nullable=False),
        sa.Column("target_key", sa.String(length=120), nullable=False),
        sa.Column("percentage", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("profile", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "level", "target_key", name="uq_user_target_level_key"),
    )
    op.create_index(op.f("ix_target_allocations_user_id"), "target_allocations", ["user_id"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("type", sa.String(length=12), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("fees", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("broker", sa.String(length=120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transactions_asset_id"), "transactions", ["asset_id"], unique=False)
    op.create_index(op.f("ix_transactions_user_id"), "transactions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_user_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_asset_id"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_index(op.f("ix_target_allocations_user_id"), table_name="target_allocations")
    op.drop_table("target_allocations")
    op.drop_table("market_snapshots")
    op.drop_index(op.f("ix_dividends_user_id"), table_name="dividends")
    op.drop_index(op.f("ix_dividends_asset_id"), table_name="dividends")
    op.drop_table("dividends")
    op.drop_index(op.f("ix_alpha_events_user_id"), table_name="alpha_events")
    op.drop_index(op.f("ix_alpha_events_type"), table_name="alpha_events")
    op.drop_index(op.f("ix_alpha_events_status"), table_name="alpha_events")
    op.drop_index(op.f("ix_alpha_events_severity"), table_name="alpha_events")
    op.drop_index(op.f("ix_alpha_events_origin"), table_name="alpha_events")
    op.drop_index(op.f("ix_alpha_events_occurred_at"), table_name="alpha_events")
    op.drop_index(op.f("ix_alpha_events_category"), table_name="alpha_events")
    op.drop_index(op.f("ix_alpha_events_asset_id"), table_name="alpha_events")
    op.drop_table("alpha_events")
    op.drop_index(op.f("ix_alerts_user_id"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(op.f("ix_assets_ticker"), table_name="assets")
    op.drop_index(op.f("ix_assets_sector"), table_name="assets")
    op.drop_index(op.f("ix_assets_asset_class"), table_name="assets")
    op.drop_table("assets")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
