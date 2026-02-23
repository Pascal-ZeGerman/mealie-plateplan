"""Add preference columns and seed ratings table

Revision ID: 20260223_add_pref_cols
Revises:
Create Date: 2026-02-23

Adds JSON text columns for cuisine/allergy/diet preferences and family
composition to ai_addon_user_preferences. Creates ai_addon_seed_ratings
table for ONB-02 seed recipe ratings. Adds unique constraint on user_id.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260223_add_pref_cols"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add preference columns to existing ai_addon_user_preferences table.
    # batch_alter_table is required for SQLite -- it creates a temp table,
    # copies data, drops original, and renames. server_default must be a
    # string literal for SQLite compatibility.
    with op.batch_alter_table("ai_addon_user_preferences") as batch_op:
        batch_op.add_column(
            sa.Column("cuisine_preferences_json", sa.Text(), nullable=False, server_default="{}")
        )
        batch_op.add_column(
            sa.Column("allergies_json", sa.Text(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("dietary_restrictions_json", sa.Text(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("family_adults", sa.Integer(), nullable=False, server_default="2")
        )
        batch_op.add_column(
            sa.Column("family_teens", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("family_children", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("family_toddlers", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("portion_override", sa.Float(), nullable=True))
        # Make user_id unique (was just indexed before)
        batch_op.create_unique_constraint(
            "uq_ai_addon_user_preferences_user_id", ["user_id"]
        )

    # Create seed ratings table for ONB-02 recipe ratings
    op.create_table(
        "ai_addon_seed_ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("recipe_slug", sa.String(), nullable=False),
        sa.Column("recipe_name", sa.String(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_addon_seed_ratings")
    with op.batch_alter_table("ai_addon_user_preferences") as batch_op:
        batch_op.drop_column("cuisine_preferences_json")
        batch_op.drop_column("allergies_json")
        batch_op.drop_column("dietary_restrictions_json")
        batch_op.drop_column("family_adults")
        batch_op.drop_column("family_teens")
        batch_op.drop_column("family_children")
        batch_op.drop_column("family_toddlers")
        batch_op.drop_column("portion_override")
        batch_op.drop_constraint("uq_ai_addon_user_preferences_user_id")
