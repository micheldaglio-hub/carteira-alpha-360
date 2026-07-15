"""performance attribution foundation

Revision ID: 20260714_0012
Revises: 20260714_0011
Create Date: 2026-07-14 00:12:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0012"
down_revision = "20260714_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_attribution_runs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=True),
        sa.Column("publication_version_id", sa.String(length=32), nullable=True),
        sa.Column("period", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("benchmark_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("portfolio_return_pct", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("benchmark_return_pct", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("excess_return_pct", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("price_return_pct", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("income_return_pct", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("data_quality_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("source_engine", sa.String(length=120), nullable=False, server_default="performance_attribution"),
        sa.Column("methodology_version", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("top_contributors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("detractors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["publication_version_id"], ["publication_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "benchmark_name",
        "created_at",
        "created_by_user_id",
        "end_date",
        "methodology_version",
        "period",
        "publication_id",
        "publication_version_id",
        "source_engine",
        "start_date",
        "status",
    ):
        op.create_index(op.f(f"ix_research_attribution_runs_{column}"), "research_attribution_runs", [column], unique=False)

    op.create_table(
        "research_attribution_assets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=True),
        sa.Column("ticker", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("asset_name", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("asset_class", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("sector", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("target_weight", sa.Numeric(precision=8, scale=4), nullable=False, server_default="0"),
        sa.Column("start_price", sa.Numeric(precision=18, scale=6), nullable=False, server_default="0"),
        sa.Column("end_price", sa.Numeric(precision=18, scale=6), nullable=False, server_default="0"),
        sa.Column("price_return_pct", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("income_return_pct", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("total_return_pct", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("contribution_pct", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("data_quality_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["research_attribution_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "asset_class",
        "asset_id",
        "created_at",
        "provider",
        "run_id",
        "sector",
        "source_type",
        "status",
        "ticker",
    ):
        op.create_index(op.f(f"ix_research_attribution_assets_{column}"), "research_attribution_assets", [column], unique=False)


def downgrade() -> None:
    for column in (
        "ticker",
        "status",
        "source_type",
        "sector",
        "run_id",
        "provider",
        "created_at",
        "asset_id",
        "asset_class",
    ):
        op.drop_index(op.f(f"ix_research_attribution_assets_{column}"), table_name="research_attribution_assets")
    op.drop_table("research_attribution_assets")

    for column in (
        "status",
        "start_date",
        "source_engine",
        "publication_version_id",
        "publication_id",
        "period",
        "methodology_version",
        "end_date",
        "created_by_user_id",
        "created_at",
        "benchmark_name",
    ):
        op.drop_index(op.f(f"ix_research_attribution_runs_{column}"), table_name="research_attribution_runs")
    op.drop_table("research_attribution_runs")
