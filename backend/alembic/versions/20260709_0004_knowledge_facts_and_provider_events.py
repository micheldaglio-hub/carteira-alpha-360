"""knowledge facts and provider events

Revision ID: 20260709_0004
Revises: 20260709_0003
Create Date: 2026-07-09 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260709_0004"
down_revision = "20260709_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_provider_events",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status_code", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_market_data_provider_events_created_at"), "market_data_provider_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_market_data_provider_events_event_type"), "market_data_provider_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_market_data_provider_events_provider"), "market_data_provider_events", ["provider"], unique=False)
    op.create_index(op.f("ix_market_data_provider_events_severity"), "market_data_provider_events", ["severity"], unique=False)

    op.create_table(
        "asset_facts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("metric_key", sa.String(length=80), nullable=False),
        sa.Column("value_numeric", sa.Numeric(precision=24, scale=6), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("period", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("raw_payload_json", sa.Text(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "source", "metric_key", "period", name="uq_asset_fact_latest_scope"),
    )
    op.create_index(op.f("ix_asset_facts_asset_id"), "asset_facts", ["asset_id"], unique=False)
    op.create_index(op.f("ix_asset_facts_as_of"), "asset_facts", ["as_of"], unique=False)
    op.create_index(op.f("ix_asset_facts_metric_key"), "asset_facts", ["metric_key"], unique=False)
    op.create_index(op.f("ix_asset_facts_period"), "asset_facts", ["period"], unique=False)
    op.create_index(op.f("ix_asset_facts_source"), "asset_facts", ["source"], unique=False)

    op.create_table(
        "asset_metric_divergences",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("metric_key", sa.String(length=80), nullable=False),
        sa.Column("primary_source", sa.String(length=80), nullable=False),
        sa.Column("comparison_source", sa.String(length=80), nullable=False),
        sa.Column("primary_value", sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column("comparison_value", sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column("divergence_pct", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_asset_metric_divergences_asset_id"), "asset_metric_divergences", ["asset_id"], unique=False)
    op.create_index(op.f("ix_asset_metric_divergences_comparison_source"), "asset_metric_divergences", ["comparison_source"], unique=False)
    op.create_index(op.f("ix_asset_metric_divergences_created_at"), "asset_metric_divergences", ["created_at"], unique=False)
    op.create_index(op.f("ix_asset_metric_divergences_metric_key"), "asset_metric_divergences", ["metric_key"], unique=False)
    op.create_index(op.f("ix_asset_metric_divergences_primary_source"), "asset_metric_divergences", ["primary_source"], unique=False)
    op.create_index(op.f("ix_asset_metric_divergences_status"), "asset_metric_divergences", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_asset_metric_divergences_status"), table_name="asset_metric_divergences")
    op.drop_index(op.f("ix_asset_metric_divergences_primary_source"), table_name="asset_metric_divergences")
    op.drop_index(op.f("ix_asset_metric_divergences_metric_key"), table_name="asset_metric_divergences")
    op.drop_index(op.f("ix_asset_metric_divergences_created_at"), table_name="asset_metric_divergences")
    op.drop_index(op.f("ix_asset_metric_divergences_comparison_source"), table_name="asset_metric_divergences")
    op.drop_index(op.f("ix_asset_metric_divergences_asset_id"), table_name="asset_metric_divergences")
    op.drop_table("asset_metric_divergences")

    op.drop_index(op.f("ix_asset_facts_source"), table_name="asset_facts")
    op.drop_index(op.f("ix_asset_facts_period"), table_name="asset_facts")
    op.drop_index(op.f("ix_asset_facts_metric_key"), table_name="asset_facts")
    op.drop_index(op.f("ix_asset_facts_as_of"), table_name="asset_facts")
    op.drop_index(op.f("ix_asset_facts_asset_id"), table_name="asset_facts")
    op.drop_table("asset_facts")

    op.drop_index(op.f("ix_market_data_provider_events_severity"), table_name="market_data_provider_events")
    op.drop_index(op.f("ix_market_data_provider_events_provider"), table_name="market_data_provider_events")
    op.drop_index(op.f("ix_market_data_provider_events_event_type"), table_name="market_data_provider_events")
    op.drop_index(op.f("ix_market_data_provider_events_created_at"), table_name="market_data_provider_events")
    op.drop_table("market_data_provider_events")
