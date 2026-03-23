import json

from sqlalchemy import Boolean, Float, Integer, String, Text, UniqueConstraint
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


class AiAddonProviderSettings(SqlAlchemyBase):
    """API keys per household per provider.
    Any household member can set or change keys for their household.
    Keys stored as plain text (masked on display). TODO: encrypt in future hardening pass.
    """

    __tablename__ = "ai_addon_provider_settings"
    __table_args__ = (UniqueConstraint("household_id", "provider", name="uq_provider_settings_hh_provider"),)

    household_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)  # "claude" | "openai"
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    # Admin-controlled: when True, household key overrides server env var key.
    # When False, server env var key takes precedence.
    household_key_priority: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AiAddonBudgetConfig(SqlAlchemyBase):
    """Weekly spend cap per household.
    Admin can set a server-wide max_cap_usd that households cannot exceed.
    """

    __tablename__ = "ai_addon_budget_config"

    household_id: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    weekly_cap_usd: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    # Server-wide maximum — NULL means no server cap enforced
    server_max_cap_usd: Mapped[float | None] = mapped_column(Float, nullable=True)


class AiAddonAiRequestLog(SqlAlchemyBase):
    """Immutable audit log of every AI API call.
    Costs pre-calculated at log time to enable simple SUM queries for budget enforcement.
    """

    __tablename__ = "ai_addon_ai_request_log"

    household_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String, nullable=False)  # "meal_planning", etc.
    provider: Mapped[str] = mapped_column(String, nullable=False)   # "claude" | "openai"
    model: Mapped[str] = mapped_column(String, nullable=False)       # actual model ID used
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    # created_at inherited from SqlAlchemyBase — used for week boundary filtering


class AiAddonTaskConfig(SqlAlchemyBase):
    """Server-wide routing: which provider tier to use for each task type.
    Only admins can write. No household scope — one config for all households.
    Phase 3 ships with no pre-seeded rows; Phase 4 registers 'meal_planning'.
    """

    __tablename__ = "ai_addon_task_config"
    __table_args__ = (UniqueConstraint("task_type", name="uq_task_config_task_type"),)

    task_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "meal_planning"
    provider_tier: Mapped[str] = mapped_column(String, nullable=False)  # key into MODEL_REGISTRY


class AiAddonMealPlanMetadata(SqlAlchemyBase):
    """Per-entry metadata for AI-generated meal plan slots.

    Links to Mealie's group_meal_plans table via group_meal_plan_id (Integer, no FK constraint).
    Tracks lock status, dining-out flag, and AI-generation provenance.
    week_start stored as "YYYY-MM-DD" string for simple filtering without date parsing.
    """

    __tablename__ = "ai_addon_meal_plan_metadata"
    __table_args__ = (
        UniqueConstraint("group_meal_plan_id", name="uq_meal_plan_metadata_plan_id"),
    )

    household_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    group_meal_plan_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dining_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    week_start: Mapped[str] = mapped_column(String, nullable=False, index=True)  # "YYYY-MM-DD"
