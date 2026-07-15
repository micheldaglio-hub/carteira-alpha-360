"""alpha research publisher foundation

Revision ID: 20260714_0008
Revises: 20260713_0007
Create Date: 2026-07-14 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0008"
down_revision = "20260713_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_publications",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_type", sa.String(length=80), nullable=False, server_default="monthly_research"),
        sa.Column("period", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("closing_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="v0.1"),
        sa.Column("author_user_id", sa.String(length=32), nullable=True),
        sa.Column("reviewer_user_id", sa.String(length=32), nullable=True),
        sa.Column("approver_user_id", sa.String(length=32), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("partial_data_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legal_disclaimer", sa.Text(), nullable=False, server_default=""),
        sa.Column("version_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("changelog_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publication_type", "period", "version", name="uq_research_publication_period_version"),
    )
    op.create_index(op.f("ix_research_publications_approver_user_id"), "research_publications", ["approver_user_id"], unique=False)
    op.create_index(op.f("ix_research_publications_author_user_id"), "research_publications", ["author_user_id"], unique=False)
    op.create_index(op.f("ix_research_publications_created_at"), "research_publications", ["created_at"], unique=False)
    op.create_index(op.f("ix_research_publications_period"), "research_publications", ["period"], unique=False)
    op.create_index(op.f("ix_research_publications_publication_type"), "research_publications", ["publication_type"], unique=False)
    op.create_index(op.f("ix_research_publications_published_at"), "research_publications", ["published_at"], unique=False)
    op.create_index(op.f("ix_research_publications_reference_date"), "research_publications", ["reference_date"], unique=False)
    op.create_index(op.f("ix_research_publications_reviewer_user_id"), "research_publications", ["reviewer_user_id"], unique=False)
    op.create_index(op.f("ix_research_publications_status"), "research_publications", ["status"], unique=False)
    op.create_index(op.f("ix_research_publications_version"), "research_publications", ["version"], unique=False)
    op.create_index(op.f("ix_research_publications_version_hash"), "research_publications", ["version_hash"], unique=False)

    op.create_table(
        "publication_versions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("version_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("readiness_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("readiness_classification", sa.String(length=40), nullable=False, server_default="incomplete"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("partial_data_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("changelog_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publication_id", "version", name="uq_publication_version_scope"),
    )
    op.create_index(op.f("ix_publication_versions_created_at"), "publication_versions", ["created_at"], unique=False)
    op.create_index(op.f("ix_publication_versions_created_by_user_id"), "publication_versions", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_publication_versions_publication_id"), "publication_versions", ["publication_id"], unique=False)
    op.create_index(op.f("ix_publication_versions_readiness_classification"), "publication_versions", ["readiness_classification"], unique=False)
    op.create_index(op.f("ix_publication_versions_status"), "publication_versions", ["status"], unique=False)
    op.create_index(op.f("ix_publication_versions_version"), "publication_versions", ["version"], unique=False)
    op.create_index(op.f("ix_publication_versions_version_hash"), "publication_versions", ["version_hash"], unique=False)

    op.create_table(
        "publication_sections",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("version_id", sa.String(length=32), nullable=False),
        sa.Column("section_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("content_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("content_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("data_gaps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("requires_human_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("approved_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["publication_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "section_key", name="uq_publication_section_version_key"),
    )
    op.create_index(op.f("ix_publication_sections_approved_by_user_id"), "publication_sections", ["approved_by_user_id"], unique=False)
    op.create_index(op.f("ix_publication_sections_created_at"), "publication_sections", ["created_at"], unique=False)
    op.create_index(op.f("ix_publication_sections_publication_id"), "publication_sections", ["publication_id"], unique=False)
    op.create_index(op.f("ix_publication_sections_section_key"), "publication_sections", ["section_key"], unique=False)
    op.create_index(op.f("ix_publication_sections_status"), "publication_sections", ["status"], unique=False)
    op.create_index(op.f("ix_publication_sections_version_id"), "publication_sections", ["version_id"], unique=False)

    op.create_table(
        "publication_assets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("version_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=True),
        sa.Column("ticker", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("asset_name", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("role", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("action", sa.String(length=40), nullable=False, server_default="maintain"),
        sa.Column("target_weight", sa.Numeric(precision=8, scale=4), nullable=False, server_default="0"),
        sa.Column("previous_weight", sa.Numeric(precision=8, scale=4), nullable=False, server_default="0"),
        sa.Column("rating", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("thesis_status", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["publication_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "asset_id", name="uq_publication_asset_version_asset"),
    )
    op.create_index(op.f("ix_publication_assets_action"), "publication_assets", ["action"], unique=False)
    op.create_index(op.f("ix_publication_assets_asset_id"), "publication_assets", ["asset_id"], unique=False)
    op.create_index(op.f("ix_publication_assets_created_at"), "publication_assets", ["created_at"], unique=False)
    op.create_index(op.f("ix_publication_assets_publication_id"), "publication_assets", ["publication_id"], unique=False)
    op.create_index(op.f("ix_publication_assets_rating"), "publication_assets", ["rating"], unique=False)
    op.create_index(op.f("ix_publication_assets_thesis_status"), "publication_assets", ["thesis_status"], unique=False)
    op.create_index(op.f("ix_publication_assets_ticker"), "publication_assets", ["ticker"], unique=False)
    op.create_index(op.f("ix_publication_assets_version_id"), "publication_assets", ["version_id"], unique=False)

    op.create_table(
        "publication_sources",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("version_id", sa.String(length=32), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("source_ref", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=220), nullable=False, server_default=""),
        sa.Column("url", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["publication_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publication_sources_created_at"), "publication_sources", ["created_at"], unique=False)
    op.create_index(op.f("ix_publication_sources_observed_at"), "publication_sources", ["observed_at"], unique=False)
    op.create_index(op.f("ix_publication_sources_provider"), "publication_sources", ["provider"], unique=False)
    op.create_index(op.f("ix_publication_sources_publication_id"), "publication_sources", ["publication_id"], unique=False)
    op.create_index(op.f("ix_publication_sources_source_ref"), "publication_sources", ["source_ref"], unique=False)
    op.create_index(op.f("ix_publication_sources_source_type"), "publication_sources", ["source_type"], unique=False)
    op.create_index(op.f("ix_publication_sources_status"), "publication_sources", ["status"], unique=False)
    op.create_index(op.f("ix_publication_sources_version_id"), "publication_sources", ["version_id"], unique=False)

    op.create_table(
        "publication_evidence",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("version_id", sa.String(length=32), nullable=True),
        sa.Column("section_id", sa.String(length=32), nullable=True),
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
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["section_id"], ["publication_sections.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["publication_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publication_evidence_created_at"), "publication_evidence", ["created_at"], unique=False)
    op.create_index(op.f("ix_publication_evidence_domain"), "publication_evidence", ["domain"], unique=False)
    op.create_index(op.f("ix_publication_evidence_evidence_id"), "publication_evidence", ["evidence_id"], unique=False)
    op.create_index(op.f("ix_publication_evidence_evidence_key"), "publication_evidence", ["evidence_key"], unique=False)
    op.create_index(op.f("ix_publication_evidence_field_name"), "publication_evidence", ["field_name"], unique=False)
    op.create_index(op.f("ix_publication_evidence_provider"), "publication_evidence", ["provider"], unique=False)
    op.create_index(op.f("ix_publication_evidence_publication_id"), "publication_evidence", ["publication_id"], unique=False)
    op.create_index(op.f("ix_publication_evidence_section_id"), "publication_evidence", ["section_id"], unique=False)
    op.create_index(op.f("ix_publication_evidence_source_type"), "publication_evidence", ["source_type"], unique=False)
    op.create_index(op.f("ix_publication_evidence_status"), "publication_evidence", ["status"], unique=False)
    op.create_index(op.f("ix_publication_evidence_version_id"), "publication_evidence", ["version_id"], unique=False)

    op.create_table(
        "publication_reviews",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("version_id", sa.String(length=32), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=32), nullable=True),
        sa.Column("decision", sa.String(length=40), nullable=False, server_default="request_changes"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("comments", sa.Text(), nullable=False, server_default=""),
        sa.Column("requested_changes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["publication_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publication_reviews_created_at"), "publication_reviews", ["created_at"], unique=False)
    op.create_index(op.f("ix_publication_reviews_decision"), "publication_reviews", ["decision"], unique=False)
    op.create_index(op.f("ix_publication_reviews_publication_id"), "publication_reviews", ["publication_id"], unique=False)
    op.create_index(op.f("ix_publication_reviews_reviewer_user_id"), "publication_reviews", ["reviewer_user_id"], unique=False)
    op.create_index(op.f("ix_publication_reviews_status"), "publication_reviews", ["status"], unique=False)
    op.create_index(op.f("ix_publication_reviews_version_id"), "publication_reviews", ["version_id"], unique=False)

    op.create_table(
        "publication_approvals",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("version_id", sa.String(length=32), nullable=False),
        sa.Column("approver_user_id", sa.String(length=32), nullable=True),
        sa.Column("decision", sa.String(length=40), nullable=False, server_default="reject_publication"),
        sa.Column("comments", sa.Text(), nullable=False, server_default=""),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["publication_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publication_approvals_approved_at"), "publication_approvals", ["approved_at"], unique=False)
    op.create_index(op.f("ix_publication_approvals_approver_user_id"), "publication_approvals", ["approver_user_id"], unique=False)
    op.create_index(op.f("ix_publication_approvals_created_at"), "publication_approvals", ["created_at"], unique=False)
    op.create_index(op.f("ix_publication_approvals_decision"), "publication_approvals", ["decision"], unique=False)
    op.create_index(op.f("ix_publication_approvals_publication_id"), "publication_approvals", ["publication_id"], unique=False)
    op.create_index(op.f("ix_publication_approvals_version_id"), "publication_approvals", ["version_id"], unique=False)

    op.create_table(
        "publication_corrections",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("version_id", sa.String(length=32), nullable=False),
        sa.Column("previous_version", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("new_version", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("correction_type", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("impact", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("approved_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["publication_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publication_corrections_approved_by_user_id"), "publication_corrections", ["approved_by_user_id"], unique=False)
    op.create_index(op.f("ix_publication_corrections_correction_type"), "publication_corrections", ["correction_type"], unique=False)
    op.create_index(op.f("ix_publication_corrections_created_at"), "publication_corrections", ["created_at"], unique=False)
    op.create_index(op.f("ix_publication_corrections_publication_id"), "publication_corrections", ["publication_id"], unique=False)
    op.create_index(op.f("ix_publication_corrections_version_id"), "publication_corrections", ["version_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_publication_corrections_version_id"), table_name="publication_corrections")
    op.drop_index(op.f("ix_publication_corrections_publication_id"), table_name="publication_corrections")
    op.drop_index(op.f("ix_publication_corrections_created_at"), table_name="publication_corrections")
    op.drop_index(op.f("ix_publication_corrections_correction_type"), table_name="publication_corrections")
    op.drop_index(op.f("ix_publication_corrections_approved_by_user_id"), table_name="publication_corrections")
    op.drop_table("publication_corrections")

    op.drop_index(op.f("ix_publication_approvals_version_id"), table_name="publication_approvals")
    op.drop_index(op.f("ix_publication_approvals_publication_id"), table_name="publication_approvals")
    op.drop_index(op.f("ix_publication_approvals_decision"), table_name="publication_approvals")
    op.drop_index(op.f("ix_publication_approvals_created_at"), table_name="publication_approvals")
    op.drop_index(op.f("ix_publication_approvals_approver_user_id"), table_name="publication_approvals")
    op.drop_index(op.f("ix_publication_approvals_approved_at"), table_name="publication_approvals")
    op.drop_table("publication_approvals")

    op.drop_index(op.f("ix_publication_reviews_version_id"), table_name="publication_reviews")
    op.drop_index(op.f("ix_publication_reviews_status"), table_name="publication_reviews")
    op.drop_index(op.f("ix_publication_reviews_reviewer_user_id"), table_name="publication_reviews")
    op.drop_index(op.f("ix_publication_reviews_publication_id"), table_name="publication_reviews")
    op.drop_index(op.f("ix_publication_reviews_decision"), table_name="publication_reviews")
    op.drop_index(op.f("ix_publication_reviews_created_at"), table_name="publication_reviews")
    op.drop_table("publication_reviews")

    op.drop_index(op.f("ix_publication_evidence_version_id"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_status"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_source_type"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_section_id"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_publication_id"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_provider"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_field_name"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_evidence_key"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_evidence_id"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_domain"), table_name="publication_evidence")
    op.drop_index(op.f("ix_publication_evidence_created_at"), table_name="publication_evidence")
    op.drop_table("publication_evidence")

    op.drop_index(op.f("ix_publication_sources_version_id"), table_name="publication_sources")
    op.drop_index(op.f("ix_publication_sources_status"), table_name="publication_sources")
    op.drop_index(op.f("ix_publication_sources_source_type"), table_name="publication_sources")
    op.drop_index(op.f("ix_publication_sources_source_ref"), table_name="publication_sources")
    op.drop_index(op.f("ix_publication_sources_publication_id"), table_name="publication_sources")
    op.drop_index(op.f("ix_publication_sources_provider"), table_name="publication_sources")
    op.drop_index(op.f("ix_publication_sources_observed_at"), table_name="publication_sources")
    op.drop_index(op.f("ix_publication_sources_created_at"), table_name="publication_sources")
    op.drop_table("publication_sources")

    op.drop_index(op.f("ix_publication_assets_version_id"), table_name="publication_assets")
    op.drop_index(op.f("ix_publication_assets_ticker"), table_name="publication_assets")
    op.drop_index(op.f("ix_publication_assets_thesis_status"), table_name="publication_assets")
    op.drop_index(op.f("ix_publication_assets_rating"), table_name="publication_assets")
    op.drop_index(op.f("ix_publication_assets_publication_id"), table_name="publication_assets")
    op.drop_index(op.f("ix_publication_assets_created_at"), table_name="publication_assets")
    op.drop_index(op.f("ix_publication_assets_asset_id"), table_name="publication_assets")
    op.drop_index(op.f("ix_publication_assets_action"), table_name="publication_assets")
    op.drop_table("publication_assets")

    op.drop_index(op.f("ix_publication_sections_version_id"), table_name="publication_sections")
    op.drop_index(op.f("ix_publication_sections_status"), table_name="publication_sections")
    op.drop_index(op.f("ix_publication_sections_section_key"), table_name="publication_sections")
    op.drop_index(op.f("ix_publication_sections_publication_id"), table_name="publication_sections")
    op.drop_index(op.f("ix_publication_sections_created_at"), table_name="publication_sections")
    op.drop_index(op.f("ix_publication_sections_approved_by_user_id"), table_name="publication_sections")
    op.drop_table("publication_sections")

    op.drop_index(op.f("ix_publication_versions_version_hash"), table_name="publication_versions")
    op.drop_index(op.f("ix_publication_versions_version"), table_name="publication_versions")
    op.drop_index(op.f("ix_publication_versions_status"), table_name="publication_versions")
    op.drop_index(op.f("ix_publication_versions_readiness_classification"), table_name="publication_versions")
    op.drop_index(op.f("ix_publication_versions_publication_id"), table_name="publication_versions")
    op.drop_index(op.f("ix_publication_versions_created_by_user_id"), table_name="publication_versions")
    op.drop_index(op.f("ix_publication_versions_created_at"), table_name="publication_versions")
    op.drop_table("publication_versions")

    op.drop_index(op.f("ix_research_publications_version_hash"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_version"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_status"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_reviewer_user_id"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_reference_date"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_published_at"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_publication_type"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_period"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_created_at"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_author_user_id"), table_name="research_publications")
    op.drop_index(op.f("ix_research_publications_approver_user_id"), table_name="research_publications")
    op.drop_table("research_publications")
