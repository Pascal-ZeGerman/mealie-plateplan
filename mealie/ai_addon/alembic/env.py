from typing import Any

import sqlalchemy as sa
from alembic import context

import mealie.ai_addon.db.models  # noqa: F401
from mealie.core.config import get_app_settings
from mealie.db.models._model_base import SqlAlchemyBase

# This is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Use the same metadata as Mealie's base so Alembic can see all tables.
# The include_object function below ensures only ai_addon_ tables are migrated.
target_metadata = SqlAlchemyBase.metadata

# Set DB url from Mealie's config
settings = get_app_settings()

if not settings.DB_URL:
    raise Exception("DB URL not set in config")

config.set_main_option("sqlalchemy.url", settings.DB_URL.replace("%", "%%"))


def include_object(object: Any, name: str, type_: str, reflected: bool, compare_to: Any) -> bool:
    """Only process tables (and their constraints/indexes) with the ai_addon_ prefix.

    This ensures that addon migrations never touch Mealie's own tables.
    """
    if type_ == "table":
        return name.startswith("ai_addon_")
    # For non-table objects (columns, constraints, indexes), check if their
    # parent table is an addon table.
    if hasattr(object, "table"):
        return object.table.name.startswith("ai_addon_")
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        version_table="ai_addon_alembic_version",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = sa.engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=sa.pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            include_object=include_object,
            version_table="ai_addon_alembic_version",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
