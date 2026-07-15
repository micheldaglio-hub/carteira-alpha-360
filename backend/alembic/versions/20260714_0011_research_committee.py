"""research committee foundation

Revision ID: 20260714_0011
Revises: 20260714_0010
Create Date: 2026-07-14 00:11:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0011"
down_revision = "20260714_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_committee_runs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=True),
        sa.Column("publication_version_id", sa.String(length=32), nullable=True),
        sa.Column("period", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("committee_type", sa.String(length=80), nullable=False, server_default="premium_research"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("decision", sa.String(length=40), nullable=False, server_default="needs_review"),
        sa.Column("readiness_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("approval_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("blocker_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vote_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_engine", sa.String(length=120), nullable=False, server_default="research_committee"),
        sa.Column("methodology_version", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("blockers_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["publication_version_id"], ["publication_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "created_at",
        "created_by_user_id",
        "committee_type",
        "decision",
        "methodology_version",
        "period",
        "publication_id",
        "publication_version_id",
        "source_engine",
        "status",
    ):
        op.create_index(op.f(f"ix_research_committee_runs_{column}"), "research_committee_runs", [column], unique=False)

    op.create_table(
        "research_committee_gate_results",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=32), nullable=False),
        sa.Column("gate_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="warn"),
        sa.Column("severity", sa.String(length=24), nullable=False, server_default="medium"),
        sa.Column("score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("weight", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("reading", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["research_committee_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("created_at", "gate_key", "run_id", "severity", "status"):
        op.create_index(
            op.f(f"ix_research_committee_gate_results_{column}"),
            "research_committee_gate_results",
            [column],
            unique=False,
        )

    op.create_table(
        "research_committee_votes",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=32), nullable=False),
        sa.Column("voter_key", sa.String(length=80), nullable=False),
        sa.Column("voter_type", sa.String(length=80), nullable=False, server_default="engine"),
        sa.Column("decision", sa.String(length=40), nullable=False, server_default="request_changes"),
        sa.Column("confidence", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("weight", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["research_committee_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("created_at", "decision", "run_id", "voter_key", "voter_type"):
        op.create_index(op.f(f"ix_research_committee_votes_{column}"), "research_committee_votes", [column], unique=False)


def downgrade() -> None:
    for column in ("voter_type", "voter_key", "run_id", "decision", "created_at"):
        op.drop_index(op.f(f"ix_research_committee_votes_{column}"), table_name="research_committee_votes")
    op.drop_table("research_committee_votes")

    for column in ("status", "severity", "run_id", "gate_key", "created_at"):
        op.drop_index(op.f(f"ix_research_committee_gate_results_{column}"), table_name="research_committee_gate_results")
    op.drop_table("research_committee_gate_results")

    for column in (
        "status",
        "source_engine",
        "publication_version_id",
        "publication_id",
        "period",
        "methodology_version",
        "decision",
        "committee_type",
        "created_by_user_id",
        "created_at",
    ):
        op.drop_index(op.f(f"ix_research_committee_runs_{column}"), table_name="research_committee_runs")
    op.drop_table("research_committee_runs")
