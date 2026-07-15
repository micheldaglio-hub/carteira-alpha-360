"""external integration snapshots

Revision ID: 20260715_0020
Revises: 20260714_0019
Create Date: 2026-07-15 00:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260715_0020"
down_revision = "20260714_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_integration_snapshots",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=True),
        sa.Column("integration_key", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("name", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="BRL"),
        sa.Column("current_balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("initial_capital", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("open_pnl", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("total_pnl", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("total_pnl_pct", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("source_payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "created_at",
        "currency",
        "integration_key",
        "name",
        "observed_at",
        "provider",
        "status",
        "user_id",
    ):
        op.create_index(op.f(f"ix_external_integration_snapshots_{column}"), "external_integration_snapshots", [column], unique=False)


def downgrade() -> None:
    for column in (
        "user_id",
        "status",
        "provider",
        "observed_at",
        "name",
        "integration_key",
        "currency",
        "created_at",
    ):
        op.drop_index(op.f(f"ix_external_integration_snapshots_{column}"), table_name="external_integration_snapshots")
    op.drop_table("external_integration_snapshots")
