from enum import Enum

from pydantic import Field

from mealie.schema._mealie.mealie_model import MealieModel


class CuisineRating(str, Enum):
    """Three-point scale for cuisine preference ratings."""

    love = "love"
    neutral = "neutral"
    dislike = "dislike"


class PreferencesUpdate(MealieModel):
    """Input schema for PUT /api/ai/preferences.

    All fields are optional to support partial auto-save (each wizard step
    only sends the fields it touched).
    """

    cuisine_preferences: dict[str, CuisineRating] | None = None
    allergies: list[str] | None = None
    dietary_restrictions: list[str] | None = None
    family_adults: int | None = Field(None, ge=0, le=20)
    family_teens: int | None = Field(None, ge=0, le=20)
    family_children: int | None = Field(None, ge=0, le=20)
    family_toddlers: int | None = Field(None, ge=0, le=20)
    portion_override: float | None = Field(None, ge=0.5, le=50.0)
    onboarding_complete: bool | None = None


class PreferencesResponse(MealieModel):
    """Full preference state returned by GET /api/ai/preferences.

    MealieModel's alias_generator (camelize) auto-converts snake_case fields
    to camelCase in JSON responses (e.g., cuisine_preferences -> cuisinePreferences).
    """

    cuisine_preferences: dict[str, str]
    allergies: list[str]
    dietary_restrictions: list[str]
    family_adults: int
    family_teens: int
    family_children: int
    family_toddlers: int
    calculated_portions: float
    portion_override: float | None
    effective_portions: float
    onboarding_complete: bool


class SeedRatingIn(MealieModel):
    """One seed recipe rating submitted by the user during onboarding (ONB-02)."""

    recipe_slug: str
    recipe_name: str
    rating: int = Field(..., ge=1, le=5)


class SeedRatingsSubmit(MealieModel):
    """Batch of seed ratings submitted when the user finishes the seed rating step."""

    ratings: list[SeedRatingIn]
