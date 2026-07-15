"""asset rating engine foundation

Revision ID: 20260714_0010
Revises: 20260714_0009
Create Date: 2026-07-14 00:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0010"
down_revision = "20260714_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_ratings",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=True),
        sa.Column("thesis_id", sa.String(length=32), nullable=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("asset_name", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("asset_class", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("rating_type", sa.String(length=80), nullable=False, server_default="institutional"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("current_version", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("current_version_id", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("current_version_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("current_rating", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("current_classification", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("current_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("risk_level", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("source_engine", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["thesis_id"], ["asset_theses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "asset_class", "rating_type", name="uq_asset_rating_scope"),
    )
    op.create_index(op.f("ix_asset_ratings_asset_class"), "asset_ratings", ["asset_class"], unique=False)
    op.create_index(op.f("ix_asset_ratings_asset_id"), "asset_ratings", ["asset_id"], unique=False)
    op.create_index(op.f("ix_asset_ratings_created_at"), "asset_ratings", ["created_at"], unique=False)
    op.create_index(op.f("ix_asset_ratings_current_classification"), "asset_ratings", ["current_classification"], unique=False)
    op.create_index(op.f("ix_asset_ratings_current_rating"), "asset_ratings", ["current_rating"], unique=False)
    op.create_index(op.f("ix_asset_ratings_current_version"), "asset_ratings", ["current_version"], unique=False)
    op.create_index(op.f("ix_asset_ratings_current_version_hash"), "asset_ratings", ["current_version_hash"], unique=False)
    op.create_index(op.f("ix_asset_ratings_current_version_id"), "asset_ratings", ["current_version_id"], unique=False)
    op.create_index(op.f("ix_asset_ratings_last_reviewed_at"), "asset_ratings", ["last_reviewed_at"], unique=False)
    op.create_index(op.f("ix_asset_ratings_next_review_at"), "asset_ratings", ["next_review_at"], unique=False)
    op.create_index(op.f("ix_asset_ratings_rating_type"), "asset_ratings", ["rating_type"], unique=False)
    op.create_index(op.f("ix_asset_ratings_risk_level"), "asset_ratings", ["risk_level"], unique=False)
    op.create_index(op.f("ix_asset_ratings_source_engine"), "asset_ratings", ["source_engine"], unique=False)
    op.create_index(op.f("ix_asset_ratings_status"), "asset_ratings", ["status"], unique=False)
    op.create_index(op.f("ix_asset_ratings_thesis_id"), "asset_ratings", ["thesis_id"], unique=False)
    op.create_index(op.f("ix_asset_ratings_ticker"), "asset_ratings", ["ticker"], unique=False)

    op.create_table(
        "asset_rating_versions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("rating_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=True),
        sa.Column("thesis_id", sa.String(length=32), nullable=True),
        sa.Column("thesis_version_id", sa.String(length=32), nullable=True),
        sa.Column("publication_id", sa.String(length=32), nullable=True),
        sa.Column("publication_version_id", sa.String(length=32), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("version_hash", sa.String(length=80), nullable=False),
        sa.Column("rating", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("classification", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("rating_status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("score_final", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("thesis_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("evidence_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("conviction_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("data_quality_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("governance_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("suitability_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("risk_level", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("data_quality", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("strengths_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("watchpoints_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("limits_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("methodology_version", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("source_engine", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("source_thesis_hash", sa.String(length=80), nullable=False, server_default=""),
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
        sa.ForeignKeyConstraint(["rating_id"], ["asset_ratings.id"]),
        sa.ForeignKeyConstraint(["thesis_id"], ["asset_theses.id"]),
        sa.ForeignKeyConstraint(["thesis_version_id"], ["asset_thesis_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rating_id", "version", name="uq_asset_rating_version_scope"),
    )
    for column in (
        "asset_id",
        "classification",
        "created_at",
        "created_by_user_id",
        "data_quality",
        "effective_from",
        "effective_to",
        "methodology_version",
        "publication_id",
        "publication_version_id",
        "rating",
        "rating_id",
        "rating_status",
        "risk_level",
        "source_engine",
        "source_thesis_hash",
        "thesis_id",
        "thesis_version_id",
        "version",
        "version_hash",
    ):
        op.create_index(op.f(f"ix_asset_rating_versions_{column}"), "asset_rating_versions", [column], unique=False)

    op.create_table(
        "asset_rating_evidence",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("rating_id", sa.String(length=32), nullable=False),
        sa.Column("rating_version_id", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["rating_id"], ["asset_ratings.id"]),
        sa.ForeignKeyConstraint(["rating_version_id"], ["asset_rating_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "confidence",
        "created_at",
        "domain",
        "evidence_id",
        "evidence_key",
        "field_name",
        "provider",
        "rating_id",
        "rating_version_id",
        "source_type",
        "status",
    ):
        op.create_index(op.f(f"ix_asset_rating_evidence_{column}"), "asset_rating_evidence", [column], unique=False)


def downgrade() -> None:
    for column in (
        "status",
        "source_type",
        "rating_version_id",
        "rating_id",
        "provider",
        "field_name",
        "evidence_key",
        "evidence_id",
        "domain",
        "created_at",
        "confidence",
    ):
        op.drop_index(op.f(f"ix_asset_rating_evidence_{column}"), table_name="asset_rating_evidence")
    op.drop_table("asset_rating_evidence")

    for column in (
        "version_hash",
        "version",
        "thesis_version_id",
        "thesis_id",
        "source_thesis_hash",
        "source_engine",
        "risk_level",
        "rating_status",
        "rating_id",
        "rating",
        "publication_version_id",
        "publication_id",
        "methodology_version",
        "effective_to",
        "effective_from",
        "data_quality",
        "created_by_user_id",
        "created_at",
        "classification",
        "asset_id",
    ):
        op.drop_index(op.f(f"ix_asset_rating_versions_{column}"), table_name="asset_rating_versions")
    op.drop_table("asset_rating_versions")

    for column in (
        "ticker",
        "thesis_id",
        "status",
        "source_engine",
        "risk_level",
        "rating_type",
        "next_review_at",
        "last_reviewed_at",
        "current_version_id",
        "current_version_hash",
        "current_version",
        "current_rating",
        "current_classification",
        "created_at",
        "asset_id",
        "asset_class",
    ):
        op.drop_index(op.f(f"ix_asset_ratings_{column}"), table_name="asset_ratings")
    op.drop_table("asset_ratings")
