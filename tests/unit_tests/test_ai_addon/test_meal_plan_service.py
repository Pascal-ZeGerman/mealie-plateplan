"""Unit tests for meal plan generation service.

Tests prompt building, response parsing, and service logic.
All tests are pure unit tests — no live DB, AI API, or FastAPI required.
Uses _FakePrefs pattern from test_preferences.py for ORM property testing.
"""
import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Set required env vars before any Mealie imports that touch config
os.environ.setdefault("DATA_DIR", "/tmp/mealie-test")
os.environ.setdefault("PRODUCTION", "false")


class _FakePrefs:
    """Minimal stand-in for AiAddonUserPreference for prompt building tests."""

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


def _make_fake_recipe(name="Test Recipe", recipe_id=None):
    """Create a minimal fake recipe-like object."""
    r = MagicMock()
    r.id = recipe_id or uuid4()
    r.name = name
    r.slug = name.lower().replace(" ", "-")
    r.recipe_servings = 4
    r.recipe_category = []
    r.tags = []
    return r


# ---------------------------------------------------------------------------
# _build_system_prompt tests
# ---------------------------------------------------------------------------


def test_build_system_prompt_includes_allergies():
    """System prompt must include allergy constraints in HARD CONSTRAINTS section."""
    from mealie.ai_addon.services.meal_plan_service import _build_system_prompt

    prefs = _FakePrefs(allergies=["nut", "dairy"])
    prompt = _build_system_prompt(prefs, effective_portions=2.0)

    assert "nut" in prompt, "Expected 'nut' in system prompt"
    assert "dairy" in prompt, "Expected 'dairy' in system prompt"
    assert "HARD CONSTRAINTS" in prompt, "Expected 'HARD CONSTRAINTS' section in prompt"
    assert "NEVER" in prompt, "Expected 'NEVER' directive in prompt"


def test_allergy_exclusion_in_prompt():
    """Shellfish allergy must appear in the HARD CONSTRAINTS section."""
    from mealie.ai_addon.services.meal_plan_service import _build_system_prompt

    prefs = _FakePrefs(allergies=["shellfish"])
    prompt = _build_system_prompt(prefs, effective_portions=2.5)

    # Find the HARD CONSTRAINTS section
    hard_constraints_start = prompt.find("HARD CONSTRAINTS")
    assert hard_constraints_start != -1, "HARD CONSTRAINTS section not found"

    # shellfish must appear in the prompt
    assert "shellfish" in prompt, "Expected 'shellfish' in prompt HARD CONSTRAINTS"


def test_portion_in_prompt():
    """Effective portions must appear in the PORTIONS section of the system prompt."""
    from mealie.ai_addon.services.meal_plan_service import _build_system_prompt

    prefs = _FakePrefs(portions=2.5)
    prompt = _build_system_prompt(prefs, effective_portions=2.5)

    assert "2.5" in prompt, "Expected '2.5' (effective_portions) in system prompt"
    assert "PORTIONS" in prompt, "Expected 'PORTIONS' section in prompt"


def test_dietary_restriction_in_prompt():
    """Dietary restrictions must appear in the HARD CONSTRAINTS section."""
    from mealie.ai_addon.services.meal_plan_service import _build_system_prompt

    prefs = _FakePrefs(dietary=["vegetarian", "halal"])
    prompt = _build_system_prompt(prefs, effective_portions=2.0)

    assert "vegetarian" in prompt, "Expected 'vegetarian' in system prompt"
    assert "halal" in prompt, "Expected 'halal' in system prompt"


# ---------------------------------------------------------------------------
# _build_user_message tests
# ---------------------------------------------------------------------------


def test_build_user_message_recipe_format():
    """User message must include recipe IDs and names from the library."""
    from mealie.ai_addon.schema.meal_plan import GenerateMealPlanRequest
    from mealie.ai_addon.services.meal_plan_service import _build_user_message

    prefs = _FakePrefs()
    recipes = [
        _make_fake_recipe("Pasta Carbonara"),
        _make_fake_recipe("Chicken Tikka"),
        _make_fake_recipe("Beef Stew"),
    ]

    payload = GenerateMealPlanRequest(
        week_start=date(2026, 3, 23),
        meal_types=["dinner"],
    )
    empty_slots = [(date(2026, 3, 23), "dinner")]

    message = _build_user_message(prefs, recipes, payload, [], empty_slots)

    # All recipe names must appear
    assert "Pasta Carbonara" in message
    assert "Chicken Tikka" in message
    assert "Beef Stew" in message

    # All recipe IDs must appear
    for r in recipes:
        assert str(r.id) in message, f"Expected recipe id {r.id} in user message"


# ---------------------------------------------------------------------------
# _parse_ai_response tests
# ---------------------------------------------------------------------------


def test_parse_ai_response_valid_json():
    """Valid JSON response returns list of MealSlotPreview objects."""
    from mealie.ai_addon.services.meal_plan_service import _parse_ai_response

    recipe_id = uuid4()
    recipe = _make_fake_recipe("Pasta", recipe_id=recipe_id)
    recipe_lookup = {str(recipe_id): recipe}

    content = (
        '{"slots": [{"date": "2026-03-23", "meal_type": "dinner", "type": "recipe", '
        f'"recipe_id": "{recipe_id}", "recipe_name": "Pasta"}}]}}'
    )

    result = _parse_ai_response(content, recipe_lookup, effective_portions=2.0)

    assert len(result) == 1
    assert result[0].meal_type == "dinner"
    assert result[0].recipe_id == recipe_id
    assert result[0].effective_portions == 2.0


def test_parse_ai_response_invalid_recipe_id():
    """Slots with recipe IDs not in the library are skipped (hallucination guard)."""
    from mealie.ai_addon.services.meal_plan_service import _parse_ai_response

    fake_uuid = uuid4()  # Not in recipe_lookup
    recipe_lookup = {}  # Empty library

    content = (
        '{"slots": [{"date": "2026-03-23", "meal_type": "dinner", "type": "recipe", '
        f'"recipe_id": "{fake_uuid}", "recipe_name": "Hallucinated Recipe"}}]}}'
    )

    result = _parse_ai_response(content, recipe_lookup, effective_portions=2.0)

    # Hallucinated recipe should be skipped
    assert len(result) == 0, f"Expected 0 results after hallucination filter, got {len(result)}"


def test_parse_ai_response_strips_markdown():
    """Response wrapped in markdown code fences is parsed correctly."""
    from mealie.ai_addon.services.meal_plan_service import _parse_ai_response

    recipe_id = uuid4()
    recipe = _make_fake_recipe("Soup", recipe_id=recipe_id)
    recipe_lookup = {str(recipe_id): recipe}

    # Wrapped in ```json fences like some LLMs return
    content = (
        "```json\n"
        '{"slots": [{"date": "2026-03-24", "meal_type": "lunch", "type": "recipe", '
        f'"recipe_id": "{recipe_id}", "recipe_name": "Soup"}}]}}\n'
        "```"
    )

    result = _parse_ai_response(content, recipe_lookup, effective_portions=2.5)

    assert len(result) == 1
    assert result[0].meal_type == "lunch"
    assert result[0].recipe_id == recipe_id


def test_parse_ai_response_text_slot():
    """Text-type slots (leftover, dining out) have recipe_id=None."""
    from mealie.ai_addon.services.meal_plan_service import _parse_ai_response

    content = (
        '{"slots": [{"date": "2026-03-24", "meal_type": "lunch", "type": "text", '
        '"recipe_id": null, "title": "Leftover pasta"}]}'
    )

    result = _parse_ai_response(content, {}, effective_portions=2.0)

    assert len(result) == 1
    assert result[0].recipe_id is None
    assert result[0].slot_type == "text"
    assert result[0].title == "Leftover pasta"


# ---------------------------------------------------------------------------
# Service acceptance criteria tests
# ---------------------------------------------------------------------------


def test_service_has_required_functions():
    """meal_plan_service must export generate_meal_plan, commit_meal_plan, swap_meal."""
    from mealie.ai_addon.services import meal_plan_service

    assert hasattr(meal_plan_service, "generate_meal_plan")
    assert hasattr(meal_plan_service, "commit_meal_plan")
    assert hasattr(meal_plan_service, "swap_meal")
    assert hasattr(meal_plan_service, "get_week_plan")

    # Functions must be async
    import asyncio
    assert asyncio.iscoroutinefunction(meal_plan_service.generate_meal_plan)
    assert asyncio.iscoroutinefunction(meal_plan_service.commit_meal_plan)
    assert asyncio.iscoroutinefunction(meal_plan_service.swap_meal)
