"""Add AI meal rating table

Revision ID: 20260326_add_meal_rating
Revises: 20260322_add_meal_plan_metadata
Create Date: 2026-03-26

Creates ai_addon_meal_rating for storing per-user, per-recipe 1-5 star ratings
submitted after eating a planned meal. Supports upsert semantics via unique constraint.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260326_add_meal_rating"
down_revision = "20260322_add_meal_plan_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_addon_meal_rating",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("recipe_id", sa.String(), nullable=False, index=True),
        sa.Column("recipe_name", sa.String(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("group_meal_plan_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint("user_id", "recipe_id", name="uq_meal_rating_user_recipe"),
    )


def downgrade() -> None:
    op.drop_table("ai_addon_meal_rating")
