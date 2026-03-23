"""Unit tests for AiAddonMealPlanMetadata model and meal plan Pydantic schemas.

These tests verify correctness without a live database or running FastAPI instance.
"""
import os
from datetime import date
from uuid import uuid4

# Set required env vars before any Mealie imports that touch config
os.environ.setdefault("DATA_DIR", "/tmp/mealie-test")
os.environ.setdefault("PRODUCTION", "false")


# ---------------------------------------------------------------------------
# Model column tests
# ---------------------------------------------------------------------------


def test_metadata_columns():
    """AiAddonMealPlanMetadata must have all expected columns."""
    from mealie.ai_addon.db.models import AiAddonMealPlanMetadata

    column_names = [c.name for c in AiAddonMealPlanMetadata.__table__.columns]

    expected = [
        "household_id",
        "group_meal_plan_id",
        "is_locked",
        "is_dining_out",
        "ai_generated",
        "week_start",
    ]
    for col in expected:
        assert col in column_names, f"Expected column '{col}' in {column_names}"


def test_metadata_tablename():
    """AiAddonMealPlanMetadata must use the ai_addon_ prefix and correct table name."""
    from mealie.ai_addon.db.models import AiAddonMealPlanMetadata

    assert AiAddonMealPlanMetadata.__tablename__ == "ai_addon_meal_plan_metadata"


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_preview_schema_camelcase():
    """MealPlanPreviewResponse must serialize with camelCase keys."""
    from mealie.ai_addon.schema.meal_plan import MealPlanPreviewResponse, MealSlotPreview

    slot = MealSlotPreview(
        date=date(2026, 3, 23),
        meal_type="dinner",
        slot_type="recipe",
        recipe_id=uuid4(),
        recipe_name="Pasta",
        effective_portions=2.5,
    )
    response = MealPlanPreviewResponse(
        slots=[slot],
        week_start=date(2026, 3, 23),
        recipe_count=42,
    )
    data = response.model_dump(by_alias=True)

    assert "weekStart" in data, f"Expected weekStart in {list(data.keys())}"
    assert "recipeCount" in data, f"Expected recipeCount in {list(data.keys())}"
    assert data["recipeCount"] == 42

    slot_data = data["slots"][0]
    assert "mealType" in slot_data, f"Expected mealType in {list(slot_data.keys())}"
    assert "slotType" in slot_data, f"Expected slotType in {list(slot_data.keys())}"
    assert slot_data["mealType"] == "dinner"


def test_generate_request_defaults():
    """GenerateMealPlanRequest must have correct default values."""
    from mealie.ai_addon.schema.meal_plan import GenerateMealPlanRequest

    req = GenerateMealPlanRequest(
        week_start=date(2026, 3, 23),
        meal_types=["breakfast", "lunch", "dinner"],
    )
    assert req.excluded_days == []
    assert req.special_requests == ""
    assert req.replace_unlocked is False


def test_slot_preview_text_entry():
    """MealSlotPreview with slot_type='text' allows recipe_id=None."""
    from mealie.ai_addon.schema.meal_plan import MealSlotPreview

    slot = MealSlotPreview(
        date=date(2026, 3, 23),
        meal_type="lunch",
        slot_type="text",
        title="Leftover pasta",
        effective_portions=2.5,
    )
    assert slot.recipe_id is None
    assert slot.title == "Leftover pasta"
    assert slot.slot_type == "text"


def test_commit_request_schema():
    """CommitMealPlanRequest must accept a list of MealSlotPreview entries."""
    from mealie.ai_addon.schema.meal_plan import CommitMealPlanRequest, MealSlotPreview

    slots = [
        MealSlotPreview(
            date=date(2026, 3, 23),
            meal_type="dinner",
            slot_type="recipe",
            recipe_id=uuid4(),
            recipe_name="Chicken",
            effective_portions=2.0,
        )
    ]
    req = CommitMealPlanRequest(week_start=date(2026, 3, 23), slots=slots)
    assert len(req.slots) == 1
    assert req.slots[0].meal_type == "dinner"
