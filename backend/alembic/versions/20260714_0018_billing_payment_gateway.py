"""billing payment gateway

Revision ID: 20260714_0018
Revises: 20260714_0017
Create Date: 2026-07-14 00:18:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260714_0018"
down_revision = "20260714_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_checkout_sessions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("plan_id", sa.String(length=32), nullable=False),
        sa.Column("plan_code", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("billing_cycle", sa.String(length=24), nullable=False, server_default="monthly"),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="mock"),
        sa.Column("provider_checkout_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("provider_customer_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("external_reference", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="BRL"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("checkout_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("success_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("cancel_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider_payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_billing_checkout_idempotency_key"),
        sa.UniqueConstraint("provider", "provider_checkout_id", name="uq_billing_checkout_provider_id"),
    )
    for column in (
        "billing_cycle",
        "completed_at",
        "created_at",
        "expires_at",
        "external_reference",
        "idempotency_key",
        "plan_code",
        "plan_id",
        "provider",
        "provider_checkout_id",
        "provider_customer_id",
        "status",
        "user_id",
    ):
        op.create_index(op.f(f"ix_billing_checkout_sessions_{column}"), "billing_checkout_sessions", [column], unique=False)

    op.create_table(
        "billing_transactions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("checkout_session_id", sa.String(length=32), nullable=True),
        sa.Column("subscription_id", sa.String(length=32), nullable=True),
        sa.Column("plan_id", sa.String(length=32), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="mock"),
        sa.Column("provider_payment_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("external_reference", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("event_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="BRL"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["checkout_session_id"], ["billing_checkout_sessions.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["user_subscriptions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_payment_id", name="uq_billing_transactions_provider_payment"),
    )
    for column in (
        "checkout_session_id",
        "created_at",
        "event_type",
        "external_reference",
        "paid_at",
        "plan_id",
        "provider",
        "provider_payment_id",
        "status",
        "subscription_id",
        "user_id",
    ):
        op.create_index(op.f(f"ix_billing_transactions_{column}"), "billing_transactions", [column], unique=False)

    op.create_table(
        "billing_webhook_events",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="mock"),
        sa.Column("event_id", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("event_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("signature_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("checkout_session_id", sa.String(length=32), nullable=True),
        sa.Column("transaction_id", sa.String(length=32), nullable=True),
        sa.Column("raw_payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("processing_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["checkout_session_id"], ["billing_checkout_sessions.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["billing_transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_id", name="uq_billing_webhook_provider_event"),
    )
    for column in (
        "checkout_session_id",
        "event_id",
        "event_type",
        "processed_at",
        "provider",
        "received_at",
        "signature_valid",
        "status",
        "transaction_id",
    ):
        op.create_index(op.f(f"ix_billing_webhook_events_{column}"), "billing_webhook_events", [column], unique=False)


def downgrade() -> None:
    for column in (
        "transaction_id",
        "status",
        "signature_valid",
        "received_at",
        "provider",
        "processed_at",
        "event_type",
        "event_id",
        "checkout_session_id",
    ):
        op.drop_index(op.f(f"ix_billing_webhook_events_{column}"), table_name="billing_webhook_events")
    op.drop_table("billing_webhook_events")

    for column in (
        "user_id",
        "subscription_id",
        "status",
        "provider_payment_id",
        "provider",
        "plan_id",
        "paid_at",
        "external_reference",
        "event_type",
        "created_at",
        "checkout_session_id",
    ):
        op.drop_index(op.f(f"ix_billing_transactions_{column}"), table_name="billing_transactions")
    op.drop_table("billing_transactions")

    for column in (
        "user_id",
        "status",
        "provider_customer_id",
        "provider_checkout_id",
        "provider",
        "plan_id",
        "plan_code",
        "idempotency_key",
        "external_reference",
        "expires_at",
        "created_at",
        "completed_at",
        "billing_cycle",
    ):
        op.drop_index(op.f(f"ix_billing_checkout_sessions_{column}"), table_name="billing_checkout_sessions")
    op.drop_table("billing_checkout_sessions")
