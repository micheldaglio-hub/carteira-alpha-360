"""publication immutable snapshots

Revision ID: 20260714_0013
Revises: 20260714_0012
Create Date: 2026-07-14 00:13:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0013"
down_revision = "20260714_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publication_snapshots",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("publication_version_id", sa.String(length=32), nullable=False),
        sa.Column("period", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("snapshot_type", sa.String(length=80), nullable=False, server_default="approved_edition"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="locked"),
        sa.Column("version_label", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("publication_status", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("version_status", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("snapshot_hash", sa.String(length=80), nullable=False),
        sa.Column("content_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("source_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("evidence_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("approval_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("committee_run_id", sa.String(length=32), nullable=True),
        sa.Column("attribution_run_id", sa.String(length=32), nullable=True),
        sa.Column("review_id", sa.String(length=32), nullable=True),
        sa.Column("approval_id", sa.String(length=32), nullable=True),
        sa.Column("section_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("asset_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_immutable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("manifest_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["approval_id"], ["publication_approvals.id"]),
        sa.ForeignKeyConstraint(["attribution_run_id"], ["research_attribution_runs.id"]),
        sa.ForeignKeyConstraint(["committee_run_id"], ["research_committee_runs.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["publication_version_id"], ["publication_versions.id"]),
        sa.ForeignKeyConstraint(["review_id"], ["publication_reviews.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publication_version_id", "snapshot_type", name="uq_publication_snapshot_version_type"),
    )

    for column in (
        "approval_hash",
        "approval_id",
        "asset_count",
        "attribution_run_id",
        "committee_run_id",
        "content_hash",
        "created_at",
        "created_by_user_id",
        "evidence_hash",
        "evidence_count",
        "is_immutable",
        "locked_at",
        "period",
        "publication_id",
        "publication_status",
        "publication_version_id",
        "review_id",
        "section_count",
        "snapshot_hash",
        "snapshot_type",
        "source_hash",
        "source_count",
        "status",
        "version_label",
        "version_status",
    ):
        op.create_index(op.f(f"ix_publication_snapshots_{column}"), "publication_snapshots", [column], unique=column == "snapshot_hash")


def downgrade() -> None:
    for column in (
        "version_status",
        "version_label",
        "status",
        "source_count",
        "source_hash",
        "snapshot_type",
        "snapshot_hash",
        "section_count",
        "review_id",
        "publication_version_id",
        "publication_status",
        "publication_id",
        "period",
        "locked_at",
        "is_immutable",
        "evidence_count",
        "evidence_hash",
        "created_by_user_id",
        "created_at",
        "content_hash",
        "committee_run_id",
        "attribution_run_id",
        "asset_count",
        "approval_id",
        "approval_hash",
    ):
        op.drop_index(op.f(f"ix_publication_snapshots_{column}"), table_name="publication_snapshots")
    op.drop_table("publication_snapshots")
