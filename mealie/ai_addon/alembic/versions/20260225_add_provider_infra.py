"""Add AI provider infrastructure tables

Revision ID: 20260225_add_provider_infra
Revises: 20260223_add_pref_cols
Create Date: 2026-02-25

Creates four new ai_addon_ tables:
  - ai_addon_provider_settings: household API keys per provider
  - ai_addon_budget_config: per-household weekly spend cap
  - ai_addon_ai_request_log: immutable audit log of every AI call
  - ai_addon_task_config: server-wide task-type to provider-tier routing
"""
from alembic import op
import sqlalchemy as sa

revision = "20260225_add_provider_infra"
down_revision = "20260223_add_pref_cols"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_addon_provider_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("household_id", sa.String(), nullable=False, index=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column("household_key_priority", sa.Boolean(), nullable=False, server_default="1"),
        sa.UniqueConstraint("household_id", "provider", name="uq_provider_settings_hh_provider"),
    )

    op.create_table(
        "ai_addon_budget_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("household_id", sa.String(), nullable=False, index=True, unique=True),
        sa.Column("weekly_cap_usd", sa.Float(), nullable=False, server_default="10.0"),
        sa.Column("server_max_cap_usd", sa.Float(), nullable=True),
    )

    op.create_table(
        "ai_addon_ai_request_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("household_id", sa.String(), nullable=False, index=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
    )

    op.create_table(
        "ai_addon_task_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("provider_tier", sa.String(), nullable=False),
        sa.UniqueConstraint("task_type", name="uq_task_config_task_type"),
    )


def downgrade() -> None:
    op.drop_table("ai_addon_task_config")
    op.drop_table("ai_addon_ai_request_log")
    op.drop_table("ai_addon_budget_config")
    op.drop_table("ai_addon_provider_settings")
