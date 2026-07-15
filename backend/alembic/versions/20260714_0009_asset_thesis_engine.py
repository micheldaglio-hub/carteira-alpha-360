"""asset thesis engine foundation

Revision ID: 20260714_0009
Revises: 20260714_0008
Create Date: 2026-07-14 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0009"
down_revision = "20260714_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_theses",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("universal_symbol", sa.String(length=96), nullable=False, server_default=""),
        sa.Column("asset_name", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("asset_class", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("thesis_type", sa.String(length=80), nullable=False, server_default="recommended_portfolio"),
        sa.Column("strategy_profile", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("current_version", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("current_version_id", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("current_version_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("risk_level", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("source_engine", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "asset_class", "thesis_type", name="uq_asset_thesis_scope"),
    )
    op.create_index(op.f("ix_asset_theses_asset_class"), "asset_theses", ["asset_class"], unique=False)
    op.create_index(op.f("ix_asset_theses_asset_id"), "asset_theses", ["asset_id"], unique=False)
    op.create_index(op.f("ix_asset_theses_created_at"), "asset_theses", ["created_at"], unique=False)
    op.create_index(op.f("ix_asset_theses_current_version"), "asset_theses", ["current_version"], unique=False)
    op.create_index(op.f("ix_asset_theses_current_version_hash"), "asset_theses", ["current_version_hash"], unique=False)
    op.create_index(op.f("ix_asset_theses_current_version_id"), "asset_theses", ["current_version_id"], unique=False)
    op.create_index(op.f("ix_asset_theses_first_seen_at"), "asset_theses", ["first_seen_at"], unique=False)
    op.create_index(op.f("ix_asset_theses_last_reviewed_at"), "asset_theses", ["last_reviewed_at"], unique=False)
    op.create_index(op.f("ix_asset_theses_next_review_at"), "asset_theses", ["next_review_at"], unique=False)
    op.create_index(op.f("ix_asset_theses_risk_level"), "asset_theses", ["risk_level"], unique=False)
    op.create_index(op.f("ix_asset_theses_source_engine"), "asset_theses", ["source_engine"], unique=False)
    op.create_index(op.f("ix_asset_theses_status"), "asset_theses", ["status"], unique=False)
    op.create_index(op.f("ix_asset_theses_strategy_profile"), "asset_theses", ["strategy_profile"], unique=False)
    op.create_index(op.f("ix_asset_theses_thesis_type"), "asset_theses", ["thesis_type"], unique=False)
    op.create_index(op.f("ix_asset_theses_ticker"), "asset_theses", ["ticker"], unique=False)
    op.create_index(op.f("ix_asset_theses_universal_symbol"), "asset_theses", ["universal_symbol"], unique=False)

    op.create_table(
        "asset_thesis_versions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("thesis_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=True),
        sa.Column("publication_id", sa.String(length=32), nullable=True),
        sa.Column("publication_version_id", sa.String(length=32), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("version_hash", sa.String(length=80), nullable=False),
        sa.Column("thesis_status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("role", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("thesis_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("risk_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("monitoring_plan", sa.Text(), nullable=False, server_default=""),
        sa.Column("invalidation_triggers_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_report_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("source_engine", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("conviction", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("target_weight", sa.Numeric(precision=8, scale=4), nullable=False, server_default="0"),
        sa.Column("risk_level", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("data_quality", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("change_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["publication_version_id"], ["publication_versions.id"]),
        sa.ForeignKeyConstraint(["thesis_id"], ["asset_theses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thesis_id", "version", name="uq_asset_thesis_version_scope"),
    )
    op.create_index(op.f("ix_asset_thesis_versions_asset_id"), "asset_thesis_versions", ["asset_id"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_change_reason"), "asset_thesis_versions", ["change_reason"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_created_at"), "asset_thesis_versions", ["created_at"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_created_by_user_id"), "asset_thesis_versions", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_data_quality"), "asset_thesis_versions", ["data_quality"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_effective_from"), "asset_thesis_versions", ["effective_from"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_effective_to"), "asset_thesis_versions", ["effective_to"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_publication_id"), "asset_thesis_versions", ["publication_id"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_publication_version_id"), "asset_thesis_versions", ["publication_version_id"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_risk_level"), "asset_thesis_versions", ["risk_level"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_source_engine"), "asset_thesis_versions", ["source_engine"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_source_report_id"), "asset_thesis_versions", ["source_report_id"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_thesis_id"), "asset_thesis_versions", ["thesis_id"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_thesis_status"), "asset_thesis_versions", ["thesis_status"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_version"), "asset_thesis_versions", ["version"], unique=False)
    op.create_index(op.f("ix_asset_thesis_versions_version_hash"), "asset_thesis_versions", ["version_hash"], unique=False)

    op.create_table(
        "asset_thesis_evidence",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("thesis_id", sa.String(length=32), nullable=False),
        sa.Column("thesis_version_id", sa.String(length=32), nullable=False),
        sa.Column("evidence_id", sa.String(length=32), nullable=True),
        sa.Column("evidence_key", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("domain", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("field_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["data_evidence_ledger.id"]),
        sa.ForeignKeyConstraint(["thesis_id"], ["asset_theses.id"]),
        sa.ForeignKeyConstraint(["thesis_version_id"], ["asset_thesis_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_asset_thesis_evidence_confidence"), "asset_thesis_evidence", ["confidence"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_created_at"), "asset_thesis_evidence", ["created_at"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_domain"), "asset_thesis_evidence", ["domain"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_evidence_id"), "asset_thesis_evidence", ["evidence_id"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_evidence_key"), "asset_thesis_evidence", ["evidence_key"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_field_name"), "asset_thesis_evidence", ["field_name"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_provider"), "asset_thesis_evidence", ["provider"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_source_type"), "asset_thesis_evidence", ["source_type"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_status"), "asset_thesis_evidence", ["status"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_thesis_id"), "asset_thesis_evidence", ["thesis_id"], unique=False)
    op.create_index(op.f("ix_asset_thesis_evidence_thesis_version_id"), "asset_thesis_evidence", ["thesis_version_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_asset_thesis_evidence_thesis_version_id"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_thesis_id"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_status"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_source_type"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_provider"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_field_name"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_evidence_key"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_evidence_id"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_domain"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_created_at"), table_name="asset_thesis_evidence")
    op.drop_index(op.f("ix_asset_thesis_evidence_confidence"), table_name="asset_thesis_evidence")
    op.drop_table("asset_thesis_evidence")

    op.drop_index(op.f("ix_asset_thesis_versions_version_hash"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_version"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_thesis_status"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_thesis_id"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_source_report_id"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_source_engine"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_risk_level"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_publication_version_id"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_publication_id"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_effective_to"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_effective_from"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_data_quality"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_created_by_user_id"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_created_at"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_change_reason"), table_name="asset_thesis_versions")
    op.drop_index(op.f("ix_asset_thesis_versions_asset_id"), table_name="asset_thesis_versions")
    op.drop_table("asset_thesis_versions")

    op.drop_index(op.f("ix_asset_theses_universal_symbol"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_ticker"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_thesis_type"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_strategy_profile"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_status"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_source_engine"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_risk_level"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_next_review_at"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_last_reviewed_at"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_first_seen_at"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_current_version_id"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_current_version_hash"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_current_version"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_created_at"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_asset_id"), table_name="asset_theses")
    op.drop_index(op.f("ix_asset_theses_asset_class"), table_name="asset_theses")
    op.drop_table("asset_theses")
