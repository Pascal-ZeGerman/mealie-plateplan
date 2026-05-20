"""Pydantic schemas for AI meal plan generation, commit, and metadata routes.

All extend MealieModel for camelCase JSON serialization (via pyhumps alias_generator).
"""
from datetime import date
from uuid import UUID

from mealie.schema._mealie.mealie_model import MealieModel


class MealSlotPreview(MealieModel):
    """A single meal slot in a preview or committed plan."""

    date: date
    meal_type: str  # "breakfast" | "lunch" | "dinner"
    slot_type: str  # "recipe" | "text"
    recipe_id: UUID | None = None
    recipe_name: str | None = None
    recipe_slug: str | None = None
    recipe_servings: int | None = None
    title: str | None = None  # For text entries (leftover, dining out)
    effective_portions: float
    is_locked: bool = False
    is_dining_out: bool = False
    current_rating: int | None = None
    group_meal_plan_id: int | None = None


class MealPlanPreviewResponse(MealieModel):
    """Response after generating or fetching a week's meal plan preview."""

    slots: list[MealSlotPreview]
    week_start: date
    recipe_count: int  # How many recipes in library (for small library warning)


class GenerateMealPlanRequest(MealieModel):
    """Request to generate a new AI meal plan preview."""

    week_start: date
    meal_types: list[str]  # ["breakfast", "lunch", "dinner"]
    excluded_days: list[str] = []  # ["saturday", "sunday"]
    special_requests: str = ""
    replace_unlocked: bool = False  # True = replace non-locked; False = fill empty slots only


class CommitMealPlanRequest(MealieModel):
    """Request to commit a previewed meal plan to Mealie's group_meal_plans table."""

    week_start: date
    slots: list[MealSlotPreview]


class SwapMealRequest(MealieModel):
    """Request AI suggestions to swap a specific meal slot."""

    date: date
    meal_type: str  # "breakfast" | "lunch" | "dinner"
    current_recipe_id: UUID | None = None
    current_recipe_name: str | None = None


class SwapSuggestion(MealieModel):
    """One AI-suggested alternative recipe for a swap."""

    recipe_id: UUID
    recipe_name: str
    recipe_slug: str
    categories: list[str] = []
    servings: int | None = None


class SwapMealResponse(MealieModel):
    """Response containing 2-3 alternative recipe suggestions."""

    suggestions: list[SwapSuggestion]


class MetadataUpdate(MealieModel):
    """Partial update to a meal plan metadata entry (lock/dining-out flags)."""

    is_locked: bool | None = None
    is_dining_out: bool | None = None


class MetadataResponse(MealieModel):
    """Full metadata record returned after create or update."""

    id: int
    group_meal_plan_id: int
    is_locked: bool
    is_dining_out: bool
    ai_generated: bool
    week_start: str
