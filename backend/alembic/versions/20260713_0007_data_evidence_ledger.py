"""data evidence ledger

Revision ID: 20260713_0007
Revises: 20260713_0006
Create Date: 2026-07-13 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260713_0007"
down_revision = "20260713_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_evidence_ledger",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=True),
        sa.Column("asset_id", sa.String(length=32), nullable=True),
        sa.Column("trace_id", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("evidence_key", sa.String(length=160), nullable=False),
        sa.Column("domain", sa.String(length=80), nullable=False),
        sa.Column("field_name", sa.String(length=120), nullable=False),
        sa.Column("value_numeric", sa.Numeric(precision=24, scale=8), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("source_ref", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("formula_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("formula_version", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("input_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_evidence_ledger_asset_id"), "data_evidence_ledger", ["asset_id"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_created_at"), "data_evidence_ledger", ["created_at"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_domain"), "data_evidence_ledger", ["domain"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_evidence_key"), "data_evidence_ledger", ["evidence_key"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_field_name"), "data_evidence_ledger", ["field_name"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_formula_name"), "data_evidence_ledger", ["formula_name"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_input_hash"), "data_evidence_ledger", ["input_hash"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_observed_at"), "data_evidence_ledger", ["observed_at"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_provider"), "data_evidence_ledger", ["provider"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_source_type"), "data_evidence_ledger", ["source_type"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_status"), "data_evidence_ledger", ["status"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_trace_id"), "data_evidence_ledger", ["trace_id"], unique=False)
    op.create_index(op.f("ix_data_evidence_ledger_user_id"), "data_evidence_ledger", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_data_evidence_ledger_user_id"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_trace_id"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_status"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_source_type"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_provider"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_observed_at"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_input_hash"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_formula_name"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_field_name"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_evidence_key"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_domain"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_created_at"), table_name="data_evidence_ledger")
    op.drop_index(op.f("ix_data_evidence_ledger_asset_id"), table_name="data_evidence_ledger")
    op.drop_table("data_evidence_ledger")
