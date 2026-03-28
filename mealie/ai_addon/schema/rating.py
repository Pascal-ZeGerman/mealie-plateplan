"""Pydantic schemas for meal rating endpoints.

All extend MealieModel for camelCase JSON serialization (via pyhumps alias_generator).
"""
from datetime import datetime

from mealie.schema._mealie.mealie_model import MealieModel


class RatingIn(MealieModel):
    """Input schema for submitting a meal rating.

    rating=0 means clear the existing rating (delete).
    rating=1-5 means set/update the rating.
    """

    recipe_id: str
    recipe_name: str
    rating: int  # 0=clear, 1-5=set
    group_meal_plan_id: int | None = None


class RatingOut(MealieModel):
    """Output schema for a single meal rating record."""

    id: int
    recipe_id: str
    recipe_name: str
    rating: int
    updated_at: datetime | None = None  # maps to update_at from SqlAlchemyBase


class RatingHistoryResponse(MealieModel):
    """Paginated rating history response."""

    items: list[RatingOut]
    total: int


class CuisineWeightEntry(MealieModel):
    """Single cuisine weight entry for display on settings page."""

    cuisine: str
    weight: float
    has_enough_data: bool  # True if >= 3 ratings for this cuisine, False = showing baseline


class CuisineWeightsResponse(MealieModel):
    """Response with all learned cuisine weights."""

    weights: list[CuisineWeightEntry]
