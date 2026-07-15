"""distribution engine

Revision ID: 20260714_0019
Revises: 20260714_0018
Create Date: 2026-07-14 00:19:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0019"
down_revision = "20260714_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "distribution_campaigns",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("publication_id", sa.String(length=32), nullable=False),
        sa.Column("artifact_id", sa.String(length=32), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=220), nullable=False, server_default=""),
        sa.Column("channel", sa.String(length=40), nullable=False, server_default="email"),
        sa.Column("audience_type", sa.String(length=80), nullable=False, server_default="premium_subscribers"),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="mock"),
        sa.Column("provider_campaign_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("subject", sa.String(length=220), nullable=False, server_default=""),
        sa.Column("preview_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["publication_artifacts.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["research_publications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "artifact_id",
        "audience_type",
        "channel",
        "completed_at",
        "created_at",
        "created_by_user_id",
        "dispatched_at",
        "name",
        "provider",
        "provider_campaign_id",
        "publication_id",
        "scheduled_at",
        "status",
    ):
        op.create_index(op.f(f"ix_distribution_campaigns_{column}"), "distribution_campaigns", [column], unique=False)

    op.create_table(
        "distribution_recipients",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("campaign_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("provider_message_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("entitlement_status", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["distribution_campaigns.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "email", name="uq_distribution_recipient_campaign_email"),
    )
    for column in (
        "campaign_id",
        "clicked_at",
        "created_at",
        "delivered_at",
        "email",
        "entitlement_status",
        "opened_at",
        "provider_message_id",
        "sent_at",
        "status",
        "user_id",
    ):
        op.create_index(op.f(f"ix_distribution_recipients_{column}"), "distribution_recipients", [column], unique=False)

    op.create_table(
        "distribution_event_logs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("campaign_id", sa.String(length=32), nullable=False),
        sa.Column("recipient_id", sa.String(length=32), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="mock"),
        sa.Column("provider_event_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("provider_message_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("event_type", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["distribution_campaigns.id"]),
        sa.ForeignKeyConstraint(["recipient_id"], ["distribution_recipients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_distribution_event_provider_event"),
    )
    for column in (
        "campaign_id",
        "created_at",
        "event_type",
        "provider",
        "provider_event_id",
        "provider_message_id",
        "recipient_id",
        "status",
    ):
        op.create_index(op.f(f"ix_distribution_event_logs_{column}"), "distribution_event_logs", [column], unique=False)


def downgrade() -> None:
    for column in (
        "status",
        "recipient_id",
        "provider_message_id",
        "provider_event_id",
        "provider",
        "event_type",
        "created_at",
        "campaign_id",
    ):
        op.drop_index(op.f(f"ix_distribution_event_logs_{column}"), table_name="distribution_event_logs")
    op.drop_table("distribution_event_logs")

    for column in (
        "user_id",
        "status",
        "sent_at",
        "provider_message_id",
        "opened_at",
        "entitlement_status",
        "email",
        "delivered_at",
        "created_at",
        "clicked_at",
        "campaign_id",
    ):
        op.drop_index(op.f(f"ix_distribution_recipients_{column}"), table_name="distribution_recipients")
    op.drop_table("distribution_recipients")

    for column in (
        "status",
        "scheduled_at",
        "publication_id",
        "provider_campaign_id",
        "provider",
        "name",
        "dispatched_at",
        "created_by_user_id",
        "created_at",
        "completed_at",
        "channel",
        "audience_type",
        "artifact_id",
    ):
        op.drop_index(op.f(f"ix_distribution_campaigns_{column}"), table_name="distribution_campaigns")
    op.drop_table("distribution_campaigns")
