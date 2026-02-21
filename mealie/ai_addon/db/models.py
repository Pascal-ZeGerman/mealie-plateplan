from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from mealie.db.models._model_base import SqlAlchemyBase


class AiAddonConfig(SqlAlchemyBase):
    """Addon configuration per household.

    Uses loose ID references (plain String columns) rather than foreign keys
    to avoid tight coupling with Mealie's schema.
    """

    __tablename__ = "ai_addon_config"

    group_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    household_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AiAddonUserPreference(SqlAlchemyBase):
    """Per-user preference stub for future phases.

    Uses loose ID references (plain String columns) rather than foreign keys
    to avoid tight coupling with Mealie's schema.
    """

    __tablename__ = "ai_addon_user_preferences"

    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    household_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
