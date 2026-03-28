"""Unit tests for AiAddonMealRating model, rating service, and preference recalculation.

Tests cover insert/update/clear semantics, preference learning algorithm, and cuisine
weight computation. All tests are pure unit tests — no live DB or FastAPI required.
Uses in-memory SQLite session and _FakePrefs pattern.
"""
import os
from unittest.mock import MagicMock

import pytest

# Set required env vars before any Mealie imports that touch config
os.environ.setdefault("DATA_DIR", "/tmp/mealie-test")
os.environ.setdefault("PRODUCTION", "false")


# ---------------------------------------------------------------------------
# In-memory SQLite session fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite session with the AiAddonMealRating table."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from mealie.ai_addon.db.models import AiAddonMealRating, AiAddonSeedRating
    from mealie.db.models._model_base import SqlAlchemyBase

    engine = create_engine("sqlite:///:memory:", echo=False)
    # Create only the addon tables we need
    AiAddonMealRating.__table__.create(bind=engine, checkfirst=True)
    AiAddonSeedRating.__table__.create(bind=engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Fake objects for preference lookup
# ---------------------------------------------------------------------------


class _FakePrefs:
    """Minimal stand-in for AiAddonUserPreference.cuisine_preferences dict."""

    def __init__(self, cuisine_prefs=None):
        self._cuisine_prefs = cuisine_prefs or {}

    @property
    def cuisine_preferences(self) -> dict:
        return self._cuisine_prefs


def _make_recipe(name: str, recipe_id: str, slug: str, categories: list[str] | None = None):
    """Create a minimal fake recipe object for the lookup list."""
    r = MagicMock()
    r.id = recipe_id
    r.name = name
    r.slug = slug
    r.recipe_category = []
    if categories:
        for cat_name in categories:
            cat = MagicMock()
            cat.name = cat_name
            r.recipe_category.append(cat)
    return r


# ---------------------------------------------------------------------------
# Model column tests
# ---------------------------------------------------------------------------


def test_rating_model_columns():
    """AiAddonMealRating must have all expected columns."""
    from mealie.ai_addon.db.models import AiAddonMealRating

    column_names = [c.name for c in AiAddonMealRating.__table__.columns]

    expected = ["user_id", "recipe_id", "recipe_name", "rating", "group_meal_plan_id"]
    for col in expected:
        assert col in column_names, f"Expected column '{col}' in {column_names}"

    # Verify indexed columns
    indexed_cols = [c.name for c in AiAddonMealRating.__table__.columns if c.index]
    assert "user_id" in indexed_cols, "user_id must be indexed"
    assert "recipe_id" in indexed_cols, "recipe_id must be indexed"


def test_rating_model_unique_constraint():
    """AiAddonMealRating must have a UniqueConstraint on (user_id, recipe_id)."""
    from mealie.ai_addon.db.models import AiAddonMealRating

    constraint_names = [c.name for c in AiAddonMealRating.__table__.constraints]
    assert "uq_meal_rating_user_recipe" in constraint_names, (
        f"Expected UniqueConstraint 'uq_meal_rating_user_recipe' in {constraint_names}"
    )


def test_rating_model_tablename():
    """AiAddonMealRating must use the ai_addon_ prefix and correct table name."""
    from mealie.ai_addon.db.models import AiAddonMealRating

    assert AiAddonMealRating.__tablename__ == "ai_addon_meal_rating"


# ---------------------------------------------------------------------------
# submit_rating tests
# ---------------------------------------------------------------------------


def test_submit_rating_insert(db_session):
    """submit_rating() with new user_id+recipe_id creates a new row."""
    from mealie.ai_addon.services.rating_service import submit_rating

    submit_rating(db_session, "user-1", "recipe-abc", "Pasta Carbonara", 4)

    from mealie.ai_addon.db.models import AiAddonMealRating

    rows = db_session.query(AiAddonMealRating).all()
    assert len(rows) == 1
    assert rows[0].user_id == "user-1"
    assert rows[0].recipe_id == "recipe-abc"
    assert rows[0].recipe_name == "Pasta Carbonara"
    assert rows[0].rating == 4
    assert rows[0].group_meal_plan_id is None


def test_submit_rating_update(db_session):
    """submit_rating() for existing user_id+recipe_id updates rating (no duplicate row)."""
    from mealie.ai_addon.services.rating_service import submit_rating
    from mealie.ai_addon.db.models import AiAddonMealRating

    submit_rating(db_session, "user-1", "recipe-abc", "Pasta Carbonara", 4)
    submit_rating(db_session, "user-1", "recipe-abc", "Pasta Carbonara", 2, group_meal_plan_id=99)

    rows = db_session.query(AiAddonMealRating).all()
    assert len(rows) == 1, f"Expected 1 row (upsert), got {len(rows)}"
    assert rows[0].rating == 2
    assert rows[0].group_meal_plan_id == 99


def test_submit_rating_clear(db_session):
    """submit_rating() with rating=0 deletes the existing row."""
    from mealie.ai_addon.services.rating_service import submit_rating
    from mealie.ai_addon.db.models import AiAddonMealRating

    submit_rating(db_session, "user-1", "recipe-abc", "Pasta Carbonara", 5)
    submit_rating(db_session, "user-1", "recipe-abc", "Pasta Carbonara", 0)

    rows = db_session.query(AiAddonMealRating).all()
    assert len(rows) == 0, f"Expected 0 rows after clear, got {len(rows)}"


def test_submit_rating_clear_nonexistent(db_session):
    """submit_rating() with rating=0 and no existing row does nothing (no error)."""
    from mealie.ai_addon.services.rating_service import submit_rating
    from mealie.ai_addon.db.models import AiAddonMealRating

    # Should not raise
    submit_rating(db_session, "user-1", "recipe-xyz", "Unknown Recipe", 0)

    rows = db_session.query(AiAddonMealRating).all()
    assert len(rows) == 0


def test_submit_rating_with_group_meal_plan_id(db_session):
    """submit_rating() stores group_meal_plan_id when provided."""
    from mealie.ai_addon.services.rating_service import submit_rating
    from mealie.ai_addon.db.models import AiAddonMealRating

    submit_rating(db_session, "user-2", "recipe-xyz", "Chicken Tikka", 3, group_meal_plan_id=42)

    row = db_session.query(AiAddonMealRating).first()
    assert row.group_meal_plan_id == 42


# ---------------------------------------------------------------------------
# recalculate_preferences tests
# ---------------------------------------------------------------------------


def test_recalculate_no_ratings(db_session):
    """recalculate_preferences() with no seed or meal ratings returns empty LearnedPreferences."""
    from mealie.ai_addon.services.rating_service import recalculate_preferences

    prefs = _FakePrefs(cuisine_prefs={})
    recipe_lookup = []

    learned = recalculate_preferences(db_session, "user-none", prefs, recipe_lookup)

    assert learned.top_rated_recipes == []
    assert learned.low_rated_recipes == []
    assert learned.cuisine_weights == {}


def test_recalculate_combines_seed_and_meal(db_session):
    """Meal ratings override seed ratings for same recipe; both appear in combined results."""
    from mealie.ai_addon.db.models import AiAddonSeedRating, AiAddonMealRating
    from mealie.ai_addon.services.rating_service import recalculate_preferences

    recipe_id_a = "recipe-id-aaa"
    recipe_id_b = "recipe-id-bbb"

    # Seed rating for recipe B (slug-based)
    seed = AiAddonSeedRating(
        user_id="user-test",
        recipe_slug="recipe-b",
        recipe_name="Recipe B",
        rating=4,
    )
    db_session.add(seed)

    # Meal rating for recipe A (high rating)
    meal_a = AiAddonMealRating(
        user_id="user-test",
        recipe_id=recipe_id_a,
        recipe_name="Recipe A",
        rating=5,
    )
    db_session.add(meal_a)
    db_session.commit()

    prefs = _FakePrefs()
    recipe_lookup = [
        _make_recipe("Recipe A", recipe_id_a, "recipe-a"),
        _make_recipe("Recipe B", recipe_id_b, "recipe-b"),
    ]

    learned = recalculate_preferences(db_session, "user-test", prefs, recipe_lookup)

    # Recipe A (rating 5) must be in top_rated
    assert "Recipe A" in learned.top_rated_recipes, f"Expected Recipe A in top_rated: {learned.top_rated_recipes}"
    # Recipe B (seed rating 4) must also be in top_rated (combined from seed)
    assert "Recipe B" in learned.top_rated_recipes, f"Expected Recipe B in top_rated: {learned.top_rated_recipes}"


def test_recalculate_meal_overrides_seed(db_session):
    """Meal rating overrides seed rating for the same recipe_id."""
    from mealie.ai_addon.db.models import AiAddonSeedRating, AiAddonMealRating
    from mealie.ai_addon.services.rating_service import recalculate_preferences

    recipe_id = "recipe-id-override"

    # Seed says 5 stars
    seed = AiAddonSeedRating(
        user_id="user-test",
        recipe_slug="override-recipe",
        recipe_name="Override Recipe",
        rating=5,
    )
    db_session.add(seed)

    # Meal rating says 1 star (should override seed)
    meal = AiAddonMealRating(
        user_id="user-test",
        recipe_id=recipe_id,
        recipe_name="Override Recipe",
        rating=1,
    )
    db_session.add(meal)
    db_session.commit()

    prefs = _FakePrefs()
    recipe_lookup = [_make_recipe("Override Recipe", recipe_id, "override-recipe")]

    learned = recalculate_preferences(db_session, "user-test", prefs, recipe_lookup)

    # Must be in low_rated (meal rating=1 wins over seed rating=5)
    assert "Override Recipe" in learned.low_rated_recipes, (
        f"Expected Override Recipe in low_rated: {learned.low_rated_recipes}"
    )
    assert "Override Recipe" not in learned.top_rated_recipes, (
        f"Override Recipe should not be in top_rated: {learned.top_rated_recipes}"
    )


def test_cuisine_weight_below_threshold(db_session):
    """Cuisine with fewer than 3 rated recipes keeps baseline weight (D-15)."""
    from mealie.ai_addon.db.models import AiAddonMealRating
    from mealie.ai_addon.services.rating_service import recalculate_preferences

    # Add only 2 ratings for Italian recipes
    for i in range(2):
        db_session.add(AiAddonMealRating(
            user_id="user-test",
            recipe_id=f"italian-recipe-{i}",
            recipe_name=f"Italian Recipe {i}",
            rating=5,
        ))
    db_session.commit()

    prefs = _FakePrefs(cuisine_prefs={"italian": "neutral"})
    recipe_lookup = [
        _make_recipe(f"Italian Recipe {i}", f"italian-recipe-{i}", f"italian-recipe-{i}", categories=["Italian"])
        for i in range(2)
    ]

    learned = recalculate_preferences(db_session, "user-test", prefs, recipe_lookup)

    # With fewer than 3 ratings, weight stays at baseline (neutral=0.5)
    assert "italian" in learned.cuisine_weights
    assert learned.cuisine_weights["italian"] == 0.5, (
        f"Expected baseline 0.5 for Italian (< 3 ratings), got {learned.cuisine_weights['italian']}"
    )


def test_cuisine_weight_above_threshold(db_session):
    """Cuisine with 3+ rated recipes computes learned weight (D-14)."""
    from mealie.ai_addon.db.models import AiAddonMealRating
    from mealie.ai_addon.services.rating_service import recalculate_preferences

    # Add 3 high-rating Italian recipes
    for i in range(3):
        db_session.add(AiAddonMealRating(
            user_id="user-test",
            recipe_id=f"it-recipe-{i}",
            recipe_name=f"Italian Dish {i}",
            rating=5,
        ))
    db_session.commit()

    prefs = _FakePrefs(cuisine_prefs={"italian": "neutral"})
    recipe_lookup = [
        _make_recipe(f"Italian Dish {i}", f"it-recipe-{i}", f"it-dish-{i}", categories=["Italian"])
        for i in range(3)
    ]

    learned = recalculate_preferences(db_session, "user-test", prefs, recipe_lookup)

    # avg=5/5=1.0 learned, baseline=0.5
    # weight = round(0.6*1.0 + 0.4*0.5, 3) = round(0.8, 3) = 0.8
    assert "italian" in learned.cuisine_weights
    expected = round(0.6 * 1.0 + 0.4 * 0.5, 3)
    assert learned.cuisine_weights["italian"] == expected, (
        f"Expected {expected} for Italian (3+ ratings), got {learned.cuisine_weights['italian']}"
    )


def test_top_rated_list(db_session):
    """Recipes with rating >= 4 appear in top_rated_recipes (up to 10)."""
    from mealie.ai_addon.db.models import AiAddonMealRating
    from mealie.ai_addon.services.rating_service import recalculate_preferences

    for i in range(5):
        db_session.add(AiAddonMealRating(
            user_id="user-test",
            recipe_id=f"top-recipe-{i}",
            recipe_name=f"Top Recipe {i}",
            rating=4 + (i % 2),  # 4 or 5
        ))
    # Add one low-rated
    db_session.add(AiAddonMealRating(
        user_id="user-test",
        recipe_id="low-recipe-0",
        recipe_name="Bad Recipe",
        rating=2,
    ))
    db_session.commit()

    prefs = _FakePrefs()
    recipe_lookup = [
        _make_recipe(f"Top Recipe {i}", f"top-recipe-{i}", f"top-recipe-{i}") for i in range(5)
    ] + [_make_recipe("Bad Recipe", "low-recipe-0", "bad-recipe")]

    learned = recalculate_preferences(db_session, "user-test", prefs, recipe_lookup)

    for i in range(5):
        assert f"Top Recipe {i}" in learned.top_rated_recipes, (
            f"Expected Top Recipe {i} in top_rated: {learned.top_rated_recipes}"
        )
    assert "Bad Recipe" not in learned.top_rated_recipes


def test_low_rated_list(db_session):
    """Recipes with rating <= 2 appear in low_rated_recipes (up to 10)."""
    from mealie.ai_addon.db.models import AiAddonMealRating
    from mealie.ai_addon.services.rating_service import recalculate_preferences

    for i in range(3):
        db_session.add(AiAddonMealRating(
            user_id="user-test",
            recipe_id=f"bad-recipe-{i}",
            recipe_name=f"Bad Recipe {i}",
            rating=1 + (i % 2),  # 1 or 2
        ))
    db_session.add(AiAddonMealRating(
        user_id="user-test",
        recipe_id="good-recipe-0",
        recipe_name="Good Recipe",
        rating=5,
    ))
    db_session.commit()

    prefs = _FakePrefs()
    recipe_lookup = [
        _make_recipe(f"Bad Recipe {i}", f"bad-recipe-{i}", f"bad-recipe-{i}") for i in range(3)
    ] + [_make_recipe("Good Recipe", "good-recipe-0", "good-recipe")]

    learned = recalculate_preferences(db_session, "user-test", prefs, recipe_lookup)

    for i in range(3):
        assert f"Bad Recipe {i}" in learned.low_rated_recipes, (
            f"Expected Bad Recipe {i} in low_rated: {learned.low_rated_recipes}"
        )
    assert "Good Recipe" not in learned.low_rated_recipes


def test_top_rated_capped_at_10(db_session):
    """top_rated_recipes list is capped at 10 items."""
    from mealie.ai_addon.db.models import AiAddonMealRating
    from mealie.ai_addon.services.rating_service import recalculate_preferences

    for i in range(15):
        db_session.add(AiAddonMealRating(
            user_id="user-test",
            recipe_id=f"recipe-{i}",
            recipe_name=f"Recipe {i}",
            rating=5,
        ))
    db_session.commit()

    prefs = _FakePrefs()
    recipe_lookup = [_make_recipe(f"Recipe {i}", f"recipe-{i}", f"recipe-{i}") for i in range(15)]

    learned = recalculate_preferences(db_session, "user-test", prefs, recipe_lookup)

    assert len(learned.top_rated_recipes) <= 10, (
        f"Expected at most 10 top_rated_recipes, got {len(learned.top_rated_recipes)}"
    )


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_rating_schemas_exist():
    """RatingIn, RatingOut, RatingHistoryResponse, CuisineWeightEntry must be importable."""
    from mealie.ai_addon.schema.rating import (
        CuisineWeightEntry,
        CuisineWeightsResponse,
        RatingHistoryResponse,
        RatingIn,
        RatingOut,
    )

    r = RatingIn(recipe_id="abc", recipe_name="Pasta", rating=4)
    assert r.recipe_id == "abc"
    assert r.rating == 4

    entry = CuisineWeightEntry(cuisine="italian", weight=0.8, has_enough_data=True)
    assert entry.cuisine == "italian"

    resp = CuisineWeightsResponse(weights=[entry])
    assert len(resp.weights) == 1


def test_rating_in_camelcase():
    """RatingIn must serialize to camelCase (recipeId, recipeName, etc.)."""
    from mealie.ai_addon.schema.rating import RatingIn

    r = RatingIn(recipe_id="abc-123", recipe_name="Pasta", rating=5, group_meal_plan_id=7)
    data = r.model_dump(by_alias=True)

    assert "recipeId" in data, f"Expected recipeId in {list(data.keys())}"
    assert "recipeName" in data, f"Expected recipeName in {list(data.keys())}"
    assert "groupMealPlanId" in data, f"Expected groupMealPlanId in {list(data.keys())}"
