"""user roles rbac

Revision ID: 20260714_0017
Revises: 20260714_0016
Create Date: 2026-07-14 00:17:00
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260714_0017"
down_revision = "20260714_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False, server_default="global"),
        sa.Column("scope_id", sa.String(length=120), nullable=False, server_default="*"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="manual"),
        sa.Column("granted_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role", "scope_type", "scope_id", name="uq_user_roles_scope"),
    )
    for column in (
        "created_at",
        "expires_at",
        "granted_by_user_id",
        "role",
        "scope_id",
        "scope_type",
        "source",
        "starts_at",
        "status",
        "user_id",
    ):
        op.create_index(op.f(f"ix_user_roles_{column}"), "user_roles", [column], unique=False)

    users = op.get_bind().execute(sa.text("SELECT id FROM users")).fetchall()
    if users:
        user_roles = sa.table(
            "user_roles",
            sa.column("id", sa.String),
            sa.column("user_id", sa.String),
            sa.column("role", sa.String),
            sa.column("scope_type", sa.String),
            sa.column("scope_id", sa.String),
            sa.column("status", sa.String),
            sa.column("source", sa.String),
            sa.column("metadata_json", sa.Text),
        )
        op.bulk_insert(
            user_roles,
            [
                {
                    "id": uuid.uuid4().hex,
                    "user_id": row[0],
                    "role": "admin",
                    "scope_type": "global",
                    "scope_id": "*",
                    "status": "active",
                    "source": "migration_backfill",
                    "metadata_json": '{"reason":"legacy_user_preserved_as_admin","migration":"20260714_0017"}',
                }
                for row in users
            ],
        )


def downgrade() -> None:
    for column in (
        "user_id",
        "status",
        "starts_at",
        "source",
        "scope_type",
        "scope_id",
        "role",
        "granted_by_user_id",
        "expires_at",
        "created_at",
    ):
        op.drop_index(op.f(f"ix_user_roles_{column}"), table_name="user_roles")
    op.drop_table("user_roles")
