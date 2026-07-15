"""premium subscriptions and entitlements

Revision ID: 20260714_0016
Revises: 20260714_0015
Create Date: 2026-07-14 00:16:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0016"
down_revision = "20260714_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("tier", sa.String(length=40), nullable=False, server_default="free"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="BRL"),
        sa.Column("monthly_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("annual_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("features_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("limits_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subscription_plans_code"), "subscription_plans", ["code"], unique=True)
    for column in ("created_at", "status", "tier"):
        op.create_index(op.f(f"ix_subscription_plans_{column}"), "subscription_plans", [column], unique=False)

    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("plan_id", sa.String(length=32), nullable=False),
        sa.Column("plan_code", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("billing_provider", sa.String(length=80), nullable=False, server_default="manual"),
        sa.Column("external_subscription_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "billing_provider",
        "canceled_at",
        "created_at",
        "current_period_end",
        "current_period_start",
        "external_subscription_id",
        "plan_code",
        "plan_id",
        "started_at",
        "status",
        "user_id",
    ):
        op.create_index(op.f(f"ix_user_subscriptions_{column}"), "user_subscriptions", [column], unique=False)

    op.create_table(
        "premium_entitlements",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("subscription_id", sa.String(length=32), nullable=True),
        sa.Column("plan_id", sa.String(length=32), nullable=True),
        sa.Column("entitlement_key", sa.String(length=120), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False, server_default="global"),
        sa.Column("scope_id", sa.String(length=120), nullable=False, server_default="*"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="subscription"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["user_subscriptions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "created_at",
        "entitlement_key",
        "expires_at",
        "plan_id",
        "scope_id",
        "scope_type",
        "source",
        "starts_at",
        "status",
        "subscription_id",
        "user_id",
    ):
        op.create_index(op.f(f"ix_premium_entitlements_{column}"), "premium_entitlements", [column], unique=False)

    op.create_table(
        "premium_access_logs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=True),
        sa.Column("artifact_id", sa.String(length=32), nullable=True),
        sa.Column("snapshot_id", sa.String(length=32), nullable=True),
        sa.Column("entitlement_id", sa.String(length=32), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.String(length=220), nullable=False, server_default=""),
        sa.Column("entitlement_key", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("artifact_hash", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("ip_address", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["publication_artifacts.id"]),
        sa.ForeignKeyConstraint(["entitlement_id"], ["premium_entitlements.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["publication_snapshots.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "action",
        "allowed",
        "artifact_hash",
        "artifact_id",
        "created_at",
        "entitlement_id",
        "entitlement_key",
        "publication_id",
        "reason",
        "snapshot_id",
        "user_id",
    ):
        op.create_index(op.f(f"ix_premium_access_logs_{column}"), "premium_access_logs", [column], unique=False)


def downgrade() -> None:
    for column in (
        "user_id",
        "snapshot_id",
        "reason",
        "publication_id",
        "entitlement_key",
        "entitlement_id",
        "created_at",
        "artifact_id",
        "artifact_hash",
        "allowed",
        "action",
    ):
        op.drop_index(op.f(f"ix_premium_access_logs_{column}"), table_name="premium_access_logs")
    op.drop_table("premium_access_logs")

    for column in (
        "user_id",
        "subscription_id",
        "status",
        "starts_at",
        "source",
        "scope_type",
        "scope_id",
        "plan_id",
        "expires_at",
        "entitlement_key",
        "created_at",
    ):
        op.drop_index(op.f(f"ix_premium_entitlements_{column}"), table_name="premium_entitlements")
    op.drop_table("premium_entitlements")

    for column in (
        "user_id",
        "status",
        "started_at",
        "plan_id",
        "plan_code",
        "external_subscription_id",
        "current_period_start",
        "current_period_end",
        "created_at",
        "canceled_at",
        "billing_provider",
    ):
        op.drop_index(op.f(f"ix_user_subscriptions_{column}"), table_name="user_subscriptions")
    op.drop_table("user_subscriptions")

    for column in ("tier", "status", "created_at"):
        op.drop_index(op.f(f"ix_subscription_plans_{column}"), table_name="subscription_plans")
    op.drop_index(op.f("ix_subscription_plans_code"), table_name="subscription_plans")
    op.drop_table("subscription_plans")
