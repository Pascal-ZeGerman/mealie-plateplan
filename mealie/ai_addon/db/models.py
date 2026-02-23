import json

from sqlalchemy import Boolean, Float, Integer, String, Text
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
    """Per-user preferences for AI meal planning.

    Uses loose ID references (plain String columns) rather than foreign keys
    to avoid tight coupling with Mealie's schema.
    Stores list/dict preference data as JSON-encoded TEXT columns.
    """

    __tablename__ = "ai_addon_user_preferences"

    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    household_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # JSON-encoded TEXT: {"italian": "love", "mexican": "neutral", ...}
    cuisine_preferences_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    # JSON-encoded TEXT: ["nut", "shellfish", "dairy"]
    allergies_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    # JSON-encoded TEXT: ["vegetarian", "halal"]
    dietary_restrictions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Family composition
    family_adults: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    family_teens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    family_children: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    family_toddlers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    portion_override: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Python-level properties for convenient access to JSON text columns

    @property
    def cuisine_preferences(self) -> dict:
        return json.loads(self.cuisine_preferences_json)

    @cuisine_preferences.setter
    def cuisine_preferences(self, val: dict) -> None:
        self.cuisine_preferences_json = json.dumps(val)

    @property
    def allergies(self) -> list:
        return json.loads(self.allergies_json)

    @allergies.setter
    def allergies(self, val: list) -> None:
        self.allergies_json = json.dumps(val)

    @property
    def dietary_restrictions(self) -> list:
        return json.loads(self.dietary_restrictions_json)

    @dietary_restrictions.setter
    def dietary_restrictions(self, val: list) -> None:
        self.dietary_restrictions_json = json.dumps(val)

    @property
    def calculated_portions(self) -> float:
        return (
            self.family_adults * 1.0
            + self.family_teens * 1.0
            + self.family_children * 0.5
            + self.family_toddlers * 0.25
        )

    @property
    def effective_portions(self) -> float:
        if self.portion_override is not None:
            return self.portion_override
        return self.calculated_portions


class AiAddonSeedRating(SqlAlchemyBase):
    """Seed recipe ratings entered during onboarding (ONB-02).

    Links a user to a Mealie recipe slug with a 1-5 star rating.
    Uses loose ID references -- no FK constraints to Mealie tables.
    """

    __tablename__ = "ai_addon_seed_ratings"

    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    recipe_slug: Mapped[str] = mapped_column(String, nullable=False)
    recipe_name: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
