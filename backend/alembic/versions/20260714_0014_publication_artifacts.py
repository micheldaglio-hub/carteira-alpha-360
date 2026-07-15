"""publication rendered artifacts

Revision ID: 20260714_0014
Revises: 20260714_0013
Create Date: 2026-07-14 00:14:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0014"
down_revision = "20260714_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publication_artifacts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("publication_version_id", sa.String(length=32), nullable=False),
        sa.Column("snapshot_id", sa.String(length=32), nullable=False),
        sa.Column("period", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("artifact_type", sa.String(length=80), nullable=False, server_default="html"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="rendered"),
        sa.Column("title", sa.String(length=220), nullable=False, server_default=""),
        sa.Column("content_type", sa.String(length=120), nullable=False, server_default="text/html; charset=utf-8"),
        sa.Column("file_extension", sa.String(length=16), nullable=False, server_default="html"),
        sa.Column("render_engine", sa.String(length=120), nullable=False, server_default="publication_render_engine"),
        sa.Column("render_version", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("source_snapshot_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("artifact_hash", sa.String(length=80), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("plain_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("manifest_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["publication_version_id"], ["publication_versions.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["publication_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "artifact_type", "render_version", name="uq_publication_artifact_snapshot_type_version"),
    )

    for column in (
        "artifact_hash",
        "artifact_type",
        "content_type",
        "created_at",
        "created_by_user_id",
        "period",
        "publication_id",
        "publication_version_id",
        "render_engine",
        "render_version",
        "snapshot_id",
        "source_snapshot_hash",
        "status",
    ):
        op.create_index(
            op.f(f"ix_publication_artifacts_{column}"),
            "publication_artifacts",
            [column],
            unique=column == "artifact_hash",
        )


def downgrade() -> None:
    for column in (
        "status",
        "source_snapshot_hash",
        "snapshot_id",
        "render_version",
        "render_engine",
        "publication_version_id",
        "publication_id",
        "period",
        "created_by_user_id",
        "created_at",
        "content_type",
        "artifact_type",
        "artifact_hash",
    ):
        op.drop_index(op.f(f"ix_publication_artifacts_{column}"), table_name="publication_artifacts")
    op.drop_table("publication_artifacts")
