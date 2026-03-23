"""Behavioral unit tests for meal plan lock persistence and dining-out entries.

Tests PLAN-04 (locked slots survive regeneration) and PLAN-05 (dining-out entries).
Uses unittest.mock for complete isolation — no live DB or AI API required.
"""
import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

# Set required env vars before any Mealie imports that touch config
os.environ.setdefault("DATA_DIR", "/tmp/mealie-test")
os.environ.setdefault("PRODUCTION", "false")


class _FakePrefs:
    """Minimal stand-in for AiAddonUserPreference for prompt testing."""

    def __init__(self, allergies=None, dietary=None, cuisines=None, portions=2.0):
        self.allergies_json = "[]" if allergies is None else __import__("json").dumps(allergies)
        self.dietary_restrictions_json = "[]" if dietary is None else __import__("json").dumps(dietary)
        self.cuisine_preferences_json = "{}" if cuisines is None else __import__("json").dumps(cuisines)
        self.family_adults = 2
        self.family_teens = 0
        self.family_children = 0
        self.family_toddlers = 0
        self.portion_override = None
        self._effective_portions = portions

    @property
    def allergies(self):
        import json
        return json.loads(self.allergies_json)

    @property
    def dietary_restrictions(self):
        import json
        return json.loads(self.dietary_restrictions_json)

    @property
    def cuisine_preferences(self):
        import json
        return json.loads(self.cuisine_preferences_json)

    @property
    def effective_portions(self):
        return self._effective_portions


class _FakeUser:
    """Minimal stand-in for PrivateUser."""

    def __init__(self):
        self.id = uuid4()
        self.group_id = uuid4()
        self.household_id = uuid4()


def _make_fake_recipe(name="Test Recipe"):
    """Create a minimal fake recipe object."""
    r = MagicMock()
    r.id = uuid4()
    r.name = name
    r.slug = name.lower().replace(" ", "-")
    r.recipe_servings = 4
    r.recipe_category = []
    r.tags = []
    return r


# ---------------------------------------------------------------------------
# PLAN-04: Locked slot survives regeneration
# ---------------------------------------------------------------------------


def test_locked_slot_survives_regen():
    """Locked slots must be preserved verbatim regardless of replace_unlocked flag.

    PLAN-04 requirement: locked meals are preserved during regeneration.
    """
    import asyncio
    from mealie.ai_addon.schema.meal_plan import GenerateMealPlanRequest
    from mealie.ai_addon.services import meal_plan_service

    locked_uuid = uuid4()
    locked_date = date(2026, 3, 23)
    week_start = date(2026, 3, 23)

    fake_recipe = _make_fake_recipe("Locked Dinner")
    fake_recipe.id = locked_uuid

    # Existing meal plan entry that is locked
    locked_entry = MagicMock()
    locked_entry.id = 42  # group_meal_plan_id
    locked_entry.date = locked_date
    locked_entry.entry_type = "dinner"
    locked_entry.recipe_id = locked_uuid
    locked_entry.recipe = fake_recipe
    locked_entry.title = ""

    # Metadata marking the entry as locked
    locked_meta = MagicMock()
    locked_meta.group_meal_plan_id = 42
    locked_meta.is_locked = True
    locked_meta.is_dining_out = False

    # AI response that tries to overwrite the locked slot with a different recipe
    ai_different_uuid = uuid4()
    ai_response_content = (
        '{"slots": [{"date": "2026-03-23", "meal_type": "dinner", "type": "recipe", '
        f'"recipe_id": "{ai_different_uuid}", "recipe_name": "AI Override"}}]}}'
    )

    session = MagicMock()
    user = _FakeUser()

    # Set up session.query chain for prefs and metadata
    def query_side_effect(model):
        from mealie.ai_addon.db.models import AiAddonMealPlanMetadata, AiAddonUserPreference
        q = MagicMock()
        if model is AiAddonUserPreference:
            q.filter_by.return_value.first.return_value = _FakePrefs(portions=2.0)
        elif model is AiAddonMealPlanMetadata:
            q.filter_by.return_value.all.return_value = [locked_meta]
        return q

    session.query.side_effect = query_side_effect

    # Mock repos
    fake_repos = MagicMock()
    fake_repos.recipes.by_user.return_value.page_all.return_value.items = [fake_recipe]
    fake_repos.meals.get_meals_by_date_range.return_value = [locked_entry]

    # AI mock response
    ai_response = MagicMock()
    ai_response.content = ai_response_content

    payload = GenerateMealPlanRequest(
        week_start=week_start,
        meal_types=["dinner"],
        replace_unlocked=False,
    )

    with (
        patch("mealie.ai_addon.services.meal_plan_service.get_repositories", return_value=fake_repos),
        patch("mealie.ai_addon.services.meal_plan_service.call_ai", new=AsyncMock(return_value=ai_response)),
    ):
        result = asyncio.get_event_loop().run_until_complete(
            meal_plan_service.generate_meal_plan(session, user, payload)
        )

    # The locked slot should be present with the ORIGINAL recipe_id (not the AI's suggestion)
    locked_slots = [s for s in result.slots if s.is_locked]
    assert len(locked_slots) >= 1, f"Expected at least one locked slot, got: {result.slots}"

    locked = locked_slots[0]
    assert locked.recipe_id == locked_uuid, (
        f"Locked slot recipe_id changed from {locked_uuid} to {locked.recipe_id}"
    )
    assert locked.is_locked is True

    # Now test with replace_unlocked=True — locked slot STILL preserved
    payload_replace = GenerateMealPlanRequest(
        week_start=week_start,
        meal_types=["dinner"],
        replace_unlocked=True,
    )

    with (
        patch("mealie.ai_addon.services.meal_plan_service.get_repositories", return_value=fake_repos),
        patch("mealie.ai_addon.services.meal_plan_service.call_ai", new=AsyncMock(return_value=ai_response)),
    ):
        result_replace = asyncio.get_event_loop().run_until_complete(
            meal_plan_service.generate_meal_plan(session, user, payload_replace)
        )

    locked_slots_replace = [s for s in result_replace.slots if s.is_locked]
    assert len(locked_slots_replace) >= 1, "Locked slot disappeared when replace_unlocked=True"
    assert locked_slots_replace[0].recipe_id == locked_uuid, (
        "Locked slot recipe_id was overwritten even with replace_unlocked=True"
    )


# ---------------------------------------------------------------------------
# PLAN-05: Dining-out entry has no recipe_id
# ---------------------------------------------------------------------------


def test_dining_out_entry():
    """Dining-out slots must produce title-only entries with no recipe_id.

    PLAN-05 requirement: commit_meal_plan writes title='Dining Out', recipe_id=None,
    and metadata.is_dining_out=True.
    """
    import asyncio
    from mealie.ai_addon.schema.meal_plan import CommitMealPlanRequest, MealSlotPreview
    from mealie.ai_addon.services import meal_plan_service

    dining_slot = MealSlotPreview(
        date=date(2026, 3, 23),
        meal_type="dinner",
        slot_type="text",
        title="Dining Out",
        effective_portions=2.0,
        is_dining_out=True,
        is_locked=False,
    )

    session = MagicMock()
    user = _FakeUser()

    # Mock the created meal plan entry result
    created_entry = MagicMock()
    created_entry.id = 99

    captured_save_entries = []

    def capture_create_one(save_entry):
        captured_save_entries.append(save_entry)
        return created_entry

    fake_repos = MagicMock()
    fake_repos.meals.create_one.side_effect = capture_create_one

    payload = CommitMealPlanRequest(
        week_start=date(2026, 3, 23),
        slots=[dining_slot],
    )

    with patch("mealie.ai_addon.services.meal_plan_service.get_repositories", return_value=fake_repos):
        result = asyncio.get_event_loop().run_until_complete(
            meal_plan_service.commit_meal_plan(session, user, payload)
        )

    # Verify a SavePlanEntry was created with title="Dining Out" and recipe_id=None
    assert len(captured_save_entries) == 1
    save_entry = captured_save_entries[0]
    assert save_entry.recipe_id is None, f"Dining out entry should have recipe_id=None, got {save_entry.recipe_id}"
    assert save_entry.title == "Dining Out", f"Expected title='Dining Out', got {save_entry.title!r}"

    # Verify metadata was created with is_dining_out=True
    session.add.assert_called_once()
    added_meta = session.add.call_args[0][0]
    from mealie.ai_addon.db.models import AiAddonMealPlanMetadata
    assert isinstance(added_meta, AiAddonMealPlanMetadata)
    assert added_meta.is_dining_out is True
    assert added_meta.group_meal_plan_id == 99

    # Return value is list of IDs
    assert result == [99]


def test_dining_out_slot_has_no_recipe_id():
    """MealSlotPreview with is_dining_out=True serializes with recipe_id=None."""
    from mealie.ai_addon.schema.meal_plan import MealSlotPreview

    slot = MealSlotPreview(
        date=date(2026, 3, 23),
        meal_type="lunch",
        slot_type="text",
        title="Dining Out",
        effective_portions=2.5,
        is_dining_out=True,
    )

    assert slot.recipe_id is None, f"Dining out slot should have recipe_id=None, got {slot.recipe_id}"
    assert slot.is_dining_out is True

    # Serialized form
    data = slot.model_dump(by_alias=True)
    assert data["recipeId"] is None, f"Serialized dining out slot should have recipeId=None, got {data['recipeId']}"
    assert data["isDiningOut"] is True
