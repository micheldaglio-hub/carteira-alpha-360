"""publication pdf artifacts

Revision ID: 20260714_0015
Revises: 20260714_0014
Create Date: 2026-07-14 00:15:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0015"
down_revision = "20260714_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("publication_artifacts", sa.Column("source_artifact_id", sa.String(length=32), nullable=True))
    op.add_column("publication_artifacts", sa.Column("binary_content", sa.LargeBinary(), nullable=True))
    op.add_column("publication_artifacts", sa.Column("content_size_bytes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("publication_artifacts", sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_index(op.f("ix_publication_artifacts_source_artifact_id"), "publication_artifacts", ["source_artifact_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_publication_artifacts_source_artifact_id"), table_name="publication_artifacts")
    op.drop_column("publication_artifacts", "page_count")
    op.drop_column("publication_artifacts", "content_size_bytes")
    op.drop_column("publication_artifacts", "binary_content")
    op.drop_column("publication_artifacts", "source_artifact_id")
