"""Unit tests for preference models, schemas, and routes.

These tests verify correctness of the extended AiAddonUserPreference model,
AiAddonSeedRating model, and Pydantic preference schemas without requiring
a live database or running FastAPI instance.
"""
import os

import pytest

# Set required env vars before any Mealie imports that touch config
os.environ.setdefault("DATA_DIR", "/tmp/mealie-test")
os.environ.setdefault("PRODUCTION", "false")

from mealie.ai_addon.db.models import AiAddonSeedRating, AiAddonUserPreference
from mealie.ai_addon.schema.preferences import (
    CuisineRating,
    PreferencesResponse,
    PreferencesUpdate,
    SeedRatingIn,
    SeedRatingsSubmit,
)


# ---------------------------------------------------------------------------
# Model column tests
# ---------------------------------------------------------------------------


def test_preference_model_columns():
    """AiAddonUserPreference must have all expected preference columns."""
    column_names = [c.name for c in AiAddonUserPreference.__table__.columns]

    expected = [
        "user_id",
        "household_id",
        "onboarding_complete",
        "cuisine_preferences_json",
        "allergies_json",
        "dietary_restrictions_json",
        "family_adults",
        "family_teens",
        "family_children",
        "family_toddlers",
        "portion_override",
    ]
    for col in expected:
        assert col in column_names, f"Expected column '{col}' in {column_names}"


class _FakePrefs:
    """Minimal stand-in for AiAddonUserPreference that holds raw column values.

    SQLAlchemy's ORM descriptors intercept all attribute access on mapped model
    instances, even without a session. This simple class lets us test the
    @property getter/setter logic by binding the property functions to a plain
    Python object with the required raw column attributes.
    """

    def __init__(self):
        self.cuisine_preferences_json = "{}"
        self.allergies_json = "[]"
        self.dietary_restrictions_json = "[]"
        self.family_adults = 2
        self.family_teens = 0
        self.family_children = 0
        self.family_toddlers = 0
        self.portion_override = None

    # Bind the property functions from AiAddonUserPreference so they operate
    # on this plain object's attributes instead of going through ORM descriptors.
    cuisine_preferences = property(
        AiAddonUserPreference.cuisine_preferences.fget,
        AiAddonUserPreference.cuisine_preferences.fset,
    )
    allergies = property(
        AiAddonUserPreference.allergies.fget,
        AiAddonUserPreference.allergies.fset,
    )
    dietary_restrictions = property(
        AiAddonUserPreference.dietary_restrictions.fget,
        AiAddonUserPreference.dietary_restrictions.fset,
    )
    calculated_portions = property(AiAddonUserPreference.calculated_portions.fget)
    effective_portions = property(AiAddonUserPreference.effective_portions.fget)


def test_preference_json_properties():
    """JSON property accessors must round-trip through json.loads/json.dumps."""
    import json as _json

    prefs = _FakePrefs()

    # Test cuisine_preferences setter updates the JSON column
    prefs.cuisine_preferences = {"italian": "love", "mexican": "neutral"}

    stored = _json.loads(prefs.cuisine_preferences_json)
    assert stored == {"italian": "love", "mexican": "neutral"}

    # Test roundtrip through getter
    retrieved = prefs.cuisine_preferences
    assert retrieved["italian"] == "love"
    assert retrieved["mexican"] == "neutral"

    # Test allergies property
    prefs.allergies = ["nut", "dairy"]
    assert _json.loads(prefs.allergies_json) == ["nut", "dairy"]
    assert prefs.allergies == ["nut", "dairy"]

    # Test dietary_restrictions property
    prefs.dietary_restrictions = ["vegetarian"]
    assert _json.loads(prefs.dietary_restrictions_json) == ["vegetarian"]
    assert prefs.dietary_restrictions == ["vegetarian"]


def test_seed_rating_model_table_name():
    """AiAddonSeedRating must use the ai_addon_ prefix and correct table name."""
    assert AiAddonSeedRating.__tablename__ == "ai_addon_seed_ratings"


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_preferences_response_camelcase():
    """PreferencesResponse must serialize field names to camelCase via MealieModel alias_generator."""
    response = PreferencesResponse(
        cuisine_preferences={"italian": "love"},
        allergies=["nut"],
        dietary_restrictions=["vegetarian"],
        family_adults=2,
        family_teens=0,
        family_children=1,
        family_toddlers=0,
        calculated_portions=2.5,
        portion_override=None,
        effective_portions=2.5,
        onboarding_complete=False,
    )
    data = response.model_dump(by_alias=True)

    # Verify camelCase keys are present
    assert "cuisinePreferences" in data, f"Expected cuisinePreferences in {list(data.keys())}"
    assert "dietaryRestrictions" in data, f"Expected dietaryRestrictions in {list(data.keys())}"
    assert "familyAdults" in data, f"Expected familyAdults in {list(data.keys())}"
    assert "calculatedPortions" in data, f"Expected calculatedPortions in {list(data.keys())}"
    assert "effectivePortions" in data, f"Expected effectivePortions in {list(data.keys())}"
    assert "onboardingComplete" in data, f"Expected onboardingComplete in {list(data.keys())}"

    # Verify values are correct
    assert data["cuisinePreferences"] == {"italian": "love"}
    assert data["allergies"] == ["nut"]
    assert data["familyAdults"] == 2
    assert data["onboardingComplete"] is False


def test_preferences_update_all_optional():
    """PreferencesUpdate must accept an empty payload (all fields optional)."""
    update = PreferencesUpdate()
    assert update.cuisine_preferences is None
    assert update.allergies is None
    assert update.dietary_restrictions is None
    assert update.family_adults is None
    assert update.onboarding_complete is None


def test_seed_rating_in_validation():
    """SeedRatingIn must enforce rating range 1-5."""
    valid = SeedRatingIn(recipe_slug="pasta-carbonara", recipe_name="Pasta Carbonara", rating=4)
    assert valid.rating == 4

    with pytest.raises(Exception):
        SeedRatingIn(recipe_slug="x", recipe_name="X", rating=0)

    with pytest.raises(Exception):
        SeedRatingIn(recipe_slug="x", recipe_name="X", rating=6)


# ---------------------------------------------------------------------------
# Calculation tests
# ---------------------------------------------------------------------------


def test_calculated_portions():
    """calculated_portions applies correct multipliers per age range."""
    prefs = _FakePrefs()
    prefs.family_adults = 2
    prefs.family_teens = 0
    prefs.family_children = 1
    prefs.family_toddlers = 0

    # 2 * 1.0 + 0 * 1.0 + 1 * 0.5 + 0 * 0.25 = 2.5
    assert prefs.calculated_portions == 2.5


def test_effective_portions_with_override():
    """effective_portions returns portion_override when set, else calculated_portions."""
    prefs = _FakePrefs()
    prefs.family_adults = 2
    prefs.family_teens = 0
    prefs.family_children = 0
    prefs.family_toddlers = 0
    prefs.portion_override = None

    # Without override: uses calculated (2 adults = 2.0)
    assert prefs.effective_portions == 2.0

    # With override: uses override value
    prefs.portion_override = 3.0
    assert prefs.effective_portions == 3.0


# ---------------------------------------------------------------------------
# Router registration tests
# ---------------------------------------------------------------------------


def test_preferences_router_paths():
    """The preferences router must expose GET and PUT at /preferences."""
    from mealie.ai_addon.routes import preferences as prefs_module

    paths = [r.path for r in prefs_module.router.routes]
    assert "/preferences" in paths or "" in paths, (
        f"Expected preference route in {paths}. Router prefix is /preferences."
    )


def test_seed_ratings_router_paths():
    """The seed_ratings router must be registered in the main addon router."""
    from mealie.ai_addon.routes import router

    # Collect all paths (including sub-router paths)
    all_paths = [r.path for r in router.routes]
    assert any("seed-ratings" in p for p in all_paths), (
        f"Expected seed-ratings path in {all_paths}"
    )


def test_main_router_includes_preference_routes():
    """The main AI addon router must include preferences and seed-ratings routes."""
    from mealie.ai_addon.routes import router

    all_paths = [r.path for r in router.routes]
    assert any("preferences" in p for p in all_paths), (
        f"Expected preferences path in {all_paths}"
    )
    assert len(all_paths) > 3, "Main router should have health, status, admin, preferences, seed-rating routes"
