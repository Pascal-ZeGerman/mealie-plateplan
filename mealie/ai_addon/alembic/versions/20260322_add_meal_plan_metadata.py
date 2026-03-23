"""Add AI meal plan metadata table

Revision ID: 20260322_add_meal_plan_metadata
Revises: 20260225_add_provider_infra
Create Date: 2026-03-22

Creates ai_addon_meal_plan_metadata for tracking lock/dining-out state per meal slot.
Links to Mealie's group_meal_plans table via group_meal_plan_id (Integer, no FK constraint).
"""
from alembic import op
import sqlalchemy as sa

revision = "20260322_add_meal_plan_metadata"
down_revision = "20260225_add_provider_infra"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_addon_meal_plan_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("household_id", sa.String(), nullable=False, index=True),
        sa.Column("group_meal_plan_id", sa.Integer(), nullable=False, index=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_dining_out", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("week_start", sa.String(), nullable=False, index=True),
        sa.UniqueConstraint("group_meal_plan_id", name="uq_meal_plan_metadata_plan_id"),
    )


def downgrade() -> None:
    op.drop_table("ai_addon_meal_plan_metadata")
