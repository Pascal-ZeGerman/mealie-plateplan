"""Meal plan generation, commit, and metadata services.

Sequence for meal plan generation:
1. Fetch user preferences from AiAddonUserPreference
2. Fetch recipe library via get_repositories().recipes
3. Fetch existing meal plan entries for merge mode
4. Fetch locked metadata to protect locked slots
5. Build AI prompt with hard constraints (allergies, dietary) and soft preferences (cuisines, portions)
6. Call call_ai() with task_type="meal_planning"
7. Parse and validate AI response (reject hallucinated recipe IDs)
8. Merge locked slots (preserved verbatim) with AI-generated slots

CRITICAL: Locked slots ALWAYS survive regeneration regardless of replace_unlocked flag.
"""
import json
import logging
import warnings
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonMealPlanMetadata, AiAddonMealRating, AiAddonUserPreference
from mealie.ai_addon.providers.protocol import AIRequest
from mealie.ai_addon.schema.meal_plan import (
    CommitMealPlanRequest,
    GenerateMealPlanRequest,
    MealPlanPreviewResponse,
    MealSlotPreview,
    MetadataResponse,
    SwapMealRequest,
    SwapMealResponse,
    SwapSuggestion,
)
from mealie.ai_addon.services.ai_service import call_ai
from mealie.ai_addon.services.rating_service import LearnedPreferences, recalculate_preferences
from mealie.repos.all_repositories import get_repositories
from mealie.schema import mapper
from mealie.schema.meal_plan.new_meal import CreatePlanEntry, PlanEntryType, SavePlanEntry
from mealie.schema.response.pagination import PaginationQuery

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt building helpers
# ---------------------------------------------------------------------------


def _build_system_prompt(
    prefs: AiAddonUserPreference,
    effective_portions: float,
    learned: "LearnedPreferences | None" = None,
) -> str:
    """Build the system prompt with hard constraints and soft preferences.

    Optionally includes learned preference data (top/low rated recipes,
    evolved cuisine weights) when available for improved AI suggestions.
    """
    allergies = prefs.allergies if hasattr(prefs, "allergies") else []
    dietary = prefs.dietary_restrictions if hasattr(prefs, "dietary_restrictions") else []
    cuisine_prefs = prefs.cuisine_preferences if hasattr(prefs, "cuisine_preferences") else {}

    loved_cuisines = [k for k, v in cuisine_prefs.items() if v == "love"]
    disliked_cuisines = [k for k, v in cuisine_prefs.items() if v == "dislike"]

    allergies_str = ", ".join(allergies) if allergies else "none"
    dietary_str = ", ".join(dietary) if dietary else "none"
    loved_str = ", ".join(loved_cuisines) if loved_cuisines else "any"
    disliked_str = ", ".join(disliked_cuisines) if disliked_cuisines else "none"

    # Build learned preference sections (FEED-03)
    learned_sections = ""
    if learned and learned.top_rated_recipes:
        top_str = ", ".join(learned.top_rated_recipes[:10])
        learned_sections += f"\nHIGHLY RATED by this user (include more of these): {top_str}"
    if learned and learned.low_rated_recipes:
        low_str = ", ".join(learned.low_rated_recipes[:10])
        learned_sections += f"\nPOORLY RATED by this user (avoid repeating): {low_str}"
    if learned and learned.cuisine_weights:
        lines = [f"  {c}: {w:.2f}" for c, w in sorted(learned.cuisine_weights.items())]
        learned_sections += "\nCUISINE WEIGHTS (0.0=avoid, 1.0=strongly prefer):\n" + "\n".join(lines)

    return f"""You are a meal planning assistant. Generate a weekly meal plan as a JSON object.

HARD CONSTRAINTS (NEVER violate):
- NEVER suggest recipes containing these allergens: {allergies_str}
- NEVER suggest recipes with these dietary conflicts: {dietary_str}
- Only use recipe IDs from the provided list. Do NOT invent recipes.

SOFT PREFERENCES:
- Prefer recipes from these cuisines: {loved_str}
- Limit recipes from these cuisines to at most 1 per week: {disliked_str}
- Avoid repeating the same recipe within the same week unless fewer than 10 recipes available.

PORTIONS:
- Household needs {effective_portions} portions per meal.
- If a recipe serves more than {effective_portions * 1.5}, insert a "leftover" text entry the next day for the same meal type.
{learned_sections}
OUTPUT FORMAT:
Respond with ONLY valid JSON matching this schema. No commentary, no markdown, no explanation.
{{"slots": [{{"date": "YYYY-MM-DD", "meal_type": "breakfast|lunch|dinner", "type": "recipe|text", "recipe_id": "uuid-or-null", "recipe_name": "name", "title": "for-text-entries-only"}}]}}"""


def _build_user_message(
    prefs: AiAddonUserPreference,
    recipes: list,
    payload: GenerateMealPlanRequest,
    existing_locked_slots: list[MealSlotPreview],
    empty_slots: list[tuple],
) -> str:
    """Build the user message with recipe library and slot fill instructions."""
    # Compact recipe list — only RecipeSummary-level data to stay within token budget
    recipe_list = []
    for r in recipes:
        recipe_list.append({
            "id": str(r.id),
            "name": r.name or "",
            "categories": [c.name for c in (r.recipe_category or []) if hasattr(c, "name")],
            "tags": [t.name for t in (r.tags or []) if hasattr(t, "name")],
            "servings": r.recipe_servings or None,
        })

    week_end = payload.week_start + timedelta(days=6)
    slots_to_fill = [
        {"date": str(dt), "meal_type": mt}
        for dt, mt in empty_slots
    ]

    message_parts = [
        f"Week: {payload.week_start} to {week_end}",
        f"Recipe library ({len(recipes)} recipes):",
        json.dumps(recipe_list, separators=(",", ":")),
        f"\nSlots to fill ({len(slots_to_fill)} slots):",
        json.dumps(slots_to_fill, separators=(",", ":")),
    ]

    if existing_locked_slots:
        locked_info = [
            {"date": str(s.date), "meal_type": s.meal_type, "recipe_name": s.recipe_name}
            for s in existing_locked_slots
        ]
        message_parts.append(f"\nAlready locked (do NOT suggest for these slots):")
        message_parts.append(json.dumps(locked_info, separators=(",", ":")))

    if payload.special_requests:
        message_parts.append(f"\nSpecial requests: {payload.special_requests}")

    message_parts.append("\nGenerate meal plan slots for the listed slots only.")

    return "\n".join(message_parts)


def _parse_ai_response(content: str, recipe_lookup: dict, effective_portions: float) -> list[MealSlotPreview]:
    """Parse AI JSON response into MealSlotPreview objects.

    Validates every recipe_id against the recipe library.
    Skips/logs slots with hallucinated IDs.
    Strips markdown fences if present.
    """
    # Strip markdown code fences
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning("AI response is not valid JSON: %s. Content: %r", e, content[:200])
        return []

    slots_data = data.get("slots", [])
    result = []

    for slot_data in slots_data:
        meal_type = slot_data.get("meal_type", "dinner")
        slot_type = slot_data.get("type", "text")
        raw_date = slot_data.get("date", "")
        recipe_id_str = slot_data.get("recipe_id")
        recipe_name = slot_data.get("recipe_name")
        title = slot_data.get("title")

        # Parse date
        try:
            slot_date = date.fromisoformat(raw_date)
        except (ValueError, TypeError):
            logger.warning("AI returned invalid date %r, skipping slot", raw_date)
            continue

        # Validate recipe_id if present
        recipe_id: UUID | None = None
        recipe_slug: str | None = None
        recipe_servings: int | None = None

        if recipe_id_str and slot_type == "recipe":
            if recipe_id_str not in recipe_lookup:
                logger.warning("AI hallucinated recipe_id %r (not in library), skipping slot", recipe_id_str)
                continue
            recipe = recipe_lookup[recipe_id_str]
            recipe_id = recipe.id
            recipe_slug = recipe.slug
            recipe_name = recipe.name
            recipe_servings = int(recipe.recipe_servings) if recipe.recipe_servings else None
        elif slot_type == "text":
            recipe_id = None

        result.append(MealSlotPreview(
            date=slot_date,
            meal_type=meal_type,
            slot_type=slot_type,
            recipe_id=recipe_id,
            recipe_name=recipe_name,
            recipe_slug=recipe_slug,
            recipe_servings=recipe_servings,
            title=title,
            effective_portions=effective_portions,
            is_locked=False,
            is_dining_out=False,
        ))

    return result


# ---------------------------------------------------------------------------
# Main service functions
# ---------------------------------------------------------------------------


async def generate_meal_plan(
    session: Session,
    user,
    payload: GenerateMealPlanRequest,
) -> MealPlanPreviewResponse:
    """Generate a meal plan preview (not committed to Mealie yet).

    1. Loads user preferences and recipe library.
    2. Fetches existing meal plan entries for the week (for merge mode).
    3. Identifies locked slots — these are ALWAYS preserved.
    4. Determines empty/available slots to fill.
    5. Calls AI with hard constraints and soft preferences.
    6. Merges: locked slots unchanged, AI fills the rest.
    """
    # 1. Fetch user preferences
    prefs = session.query(AiAddonUserPreference).filter_by(user_id=str(user.id)).first()
    effective_portions = prefs.effective_portions if prefs else 2.0

    # 2. Fetch recipe library
    repos = get_repositories(session, group_id=user.group_id, household_id=user.household_id)
    all_recipes_result = repos.recipes.by_user(user.id).page_all(
        PaginationQuery(page=1, per_page=-1)
    )
    all_recipes = all_recipes_result.items
    recipe_lookup = {str(r.id): r for r in all_recipes}

    # 2b. Recalculate learned preferences from seed + meal ratings (FEED-02, FEED-03)
    learned = recalculate_preferences(session, str(user.id), prefs, list(all_recipes)) if prefs else LearnedPreferences()

    # 3. Fetch existing meal plan entries for the week
    week_end = payload.week_start + timedelta(days=6)
    week_start_dt = datetime(payload.week_start.year, payload.week_start.month, payload.week_start.day)
    week_end_dt = datetime(week_end.year, week_end.month, week_end.day)
    existing_entries = repos.meals.get_meals_by_date_range(week_start_dt, week_end_dt)

    # Build lookup: (date_str, entry_type) -> entry
    existing_map: dict[tuple[str, str], object] = {}
    for entry in existing_entries:
        key = (str(entry.date), str(entry.entry_type))
        existing_map[key] = entry

    # 4. Fetch locked metadata for this week
    locked_meta = session.query(AiAddonMealPlanMetadata).filter_by(
        household_id=str(user.household_id),
        week_start=str(payload.week_start),
    ).all()
    locked_plan_ids = {m.group_meal_plan_id for m in locked_meta if m.is_locked}

    # Build locked slots from existing entries that have locked metadata
    locked_slots: list[MealSlotPreview] = []
    locked_keys: set[tuple[str, str]] = set()

    for entry in existing_entries:
        if getattr(entry, "id", None) in locked_plan_ids:
            recipe = getattr(entry, "recipe", None)
            locked_slots.append(MealSlotPreview(
                date=entry.date,
                meal_type=str(entry.entry_type),
                slot_type="recipe" if entry.recipe_id else "text",
                recipe_id=entry.recipe_id,
                recipe_name=recipe.name if recipe else None,
                recipe_slug=recipe.slug if recipe else None,
                recipe_servings=int(recipe.recipe_servings) if recipe and recipe.recipe_servings else None,
                title=entry.title or None,
                effective_portions=effective_portions,
                is_locked=True,
                is_dining_out=False,
            ))
            locked_keys.add((str(entry.date), str(entry.entry_type)))

    # 5. Determine which slots need to be filled
    # Build all requested (date, meal_type) combinations
    all_requested_slots: list[tuple[date, str]] = []
    excluded_days_lower = {d.lower() for d in payload.excluded_days}
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    current_date = payload.week_start
    while current_date <= week_end:
        day_name = day_names[current_date.weekday()]
        if day_name not in excluded_days_lower:
            for meal_type in payload.meal_types:
                all_requested_slots.append((current_date, meal_type))
        current_date += timedelta(days=1)

    # Determine empty slots (available for AI to fill)
    empty_slots: list[tuple[date, str]] = []
    for slot_date, meal_type in all_requested_slots:
        key = (str(slot_date), meal_type)
        if key in locked_keys:
            # Always skip locked slots — they are preserved verbatim
            continue
        if key in existing_map and not payload.replace_unlocked:
            # Slot already filled and we're not replacing unlocked — skip
            continue
        empty_slots.append((slot_date, meal_type))

    # 6. Build AI prompt and call
    if empty_slots and all_recipes:
        system_prompt = _build_system_prompt(prefs, effective_portions, learned=learned) if prefs else (
            f"You are a meal planning assistant. Return JSON with 'slots' array. "
            f"Only use recipe IDs from the provided list. "
            f'{{"slots": [{{"date": "YYYY-MM-DD", "meal_type": "breakfast|lunch|dinner", "type": "recipe|text", "recipe_id": "uuid-or-null", "recipe_name": "name", "title": "for-text-entries-only"}}]}}'
        )
        user_message = _build_user_message(prefs, all_recipes, payload, locked_slots, empty_slots)

        response = await call_ai(
            session,
            str(user.household_id),
            str(user.id),
            AIRequest(
                task_type="meal_planning",
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=4096,
            ),
        )

        ai_slots = _parse_ai_response(response.content, recipe_lookup, effective_portions)
    else:
        ai_slots = []

    # 7. Merge: locked slots first (verbatim), then AI slots
    # Filter AI slots to exclude any that overlap with locked positions
    non_locked_ai_slots = [
        s for s in ai_slots
        if (str(s.date), s.meal_type) not in locked_keys
    ]

    all_slots = locked_slots + non_locked_ai_slots

    return MealPlanPreviewResponse(
        slots=all_slots,
        week_start=payload.week_start,
        recipe_count=len(all_recipes),
    )


async def commit_meal_plan(
    session: Session,
    user,
    payload: CommitMealPlanRequest,
) -> list[int]:
    """Commit a previewed meal plan to Mealie's group_meal_plans table.

    For each slot:
    - Creates a CreatePlanEntry, casts to SavePlanEntry via mapper
    - Writes via repos.meals.create_one
    - Creates AiAddonMealPlanMetadata linking to the new meal plan entry
    Returns list of created meal plan IDs.
    """
    repos = get_repositories(session, group_id=user.group_id, household_id=user.household_id)
    created_ids: list[int] = []

    for slot in payload.slots:
        # Build the Mealie CreatePlanEntry
        if slot.is_dining_out:
            create_entry = CreatePlanEntry(
                date=slot.date,
                entry_type=PlanEntryType(slot.meal_type),
                title="Dining Out",
                recipe_id=None,
            )
        elif slot.slot_type == "text":
            create_entry = CreatePlanEntry(
                date=slot.date,
                entry_type=PlanEntryType(slot.meal_type),
                title=slot.title or "Leftover",
                recipe_id=None,
            )
        else:
            create_entry = CreatePlanEntry(
                date=slot.date,
                entry_type=PlanEntryType(slot.meal_type),
                title="",
                recipe_id=slot.recipe_id,
            )

        # Cast to SavePlanEntry and write via repository
        save_entry = mapper.cast(create_entry, SavePlanEntry, group_id=user.group_id, user_id=user.id)
        result = repos.meals.create_one(save_entry)

        # Create addon metadata record
        metadata = AiAddonMealPlanMetadata(
            household_id=str(user.household_id),
            group_meal_plan_id=result.id,
            is_locked=slot.is_locked,
            is_dining_out=slot.is_dining_out,
            ai_generated=True,
            week_start=str(payload.week_start),
        )
        session.add(metadata)
        session.commit()

        created_ids.append(result.id)

    return created_ids


async def get_week_plan(
    session: Session,
    user,
    week_start: date,
) -> MealPlanPreviewResponse:
    """Get current week's meal plan with addon metadata.

    Fetches existing Mealie entries and enriches with lock/dining-out flags
    from the addon metadata table. Returns a MealPlanPreviewResponse.
    """
    repos = get_repositories(session, group_id=user.group_id, household_id=user.household_id)

    week_end = week_start + timedelta(days=6)
    week_start_dt = datetime(week_start.year, week_start.month, week_start.day)
    week_end_dt = datetime(week_end.year, week_end.month, week_end.day)

    existing_entries = repos.meals.get_meals_by_date_range(week_start_dt, week_end_dt)

    # Fetch addon metadata for this week
    meta_records = session.query(AiAddonMealPlanMetadata).filter_by(
        household_id=str(user.household_id),
        week_start=str(week_start),
    ).all()
    meta_map = {m.group_meal_plan_id: m for m in meta_records}

    # Fetch user's meal ratings for this week's recipe slots
    user_ratings = session.query(AiAddonMealRating).filter_by(user_id=str(user.id)).all()
    rating_map = {r.recipe_id: r.rating for r in user_ratings}

    # Fetch all recipes for count
    all_recipes_result = repos.recipes.by_user(user.id).page_all(
        PaginationQuery(page=1, per_page=-1)
    )
    recipe_count = len(all_recipes_result.items)

    # Default effective_portions
    prefs = session.query(AiAddonUserPreference).filter_by(user_id=str(user.id)).first()
    effective_portions = prefs.effective_portions if prefs else 2.0

    slots: list[MealSlotPreview] = []
    for entry in existing_entries:
        meta = meta_map.get(entry.id)
        recipe = getattr(entry, "recipe", None)
        slots.append(MealSlotPreview(
            date=entry.date,
            meal_type=str(entry.entry_type),
            slot_type="recipe" if entry.recipe_id else "text",
            recipe_id=entry.recipe_id,
            recipe_name=recipe.name if recipe else None,
            recipe_slug=recipe.slug if recipe else None,
            recipe_servings=int(recipe.recipe_servings) if recipe and recipe.recipe_servings else None,
            title=entry.title or None,
            effective_portions=effective_portions,
            is_locked=meta.is_locked if meta else True,  # Manually-added = treat as locked in display
            is_dining_out=meta.is_dining_out if meta else False,
            current_rating=rating_map.get(str(entry.recipe_id)) if entry.recipe_id else None,
            group_meal_plan_id=entry.id,
        ))

    return MealPlanPreviewResponse(
        slots=slots,
        week_start=week_start,
        recipe_count=recipe_count,
    )


async def swap_meal(
    session: Session,
    user,
    payload: SwapMealRequest,
) -> SwapMealResponse:
    """Get 2-3 AI-suggested alternative recipes for a meal slot.

    Builds a lightweight prompt asking for alternatives, calls call_ai,
    and returns up to 3 SwapSuggestion objects.
    """
    repos = get_repositories(session, group_id=user.group_id, household_id=user.household_id)
    all_recipes_result = repos.recipes.by_user(user.id).page_all(
        PaginationQuery(page=1, per_page=-1)
    )
    all_recipes = all_recipes_result.items
    recipe_lookup = {str(r.id): r for r in all_recipes}

    prefs = session.query(AiAddonUserPreference).filter_by(user_id=str(user.id)).first()
    effective_portions = prefs.effective_portions if prefs else 2.0

    # Compact recipe list
    recipe_list = [
        {"id": str(r.id), "name": r.name or "", "servings": r.recipe_servings or None}
        for r in all_recipes
    ]

    current_info = ""
    if payload.current_recipe_name:
        current_info = f"\nCurrently: {payload.current_recipe_name} (id={payload.current_recipe_id})"

    system_prompt = (
        "You are a meal planning assistant. Suggest 2-3 alternative recipes for a single meal slot.\n"
        "Only use recipe IDs from the provided list. Do NOT invent recipes.\n"
        'Respond with ONLY valid JSON: {"suggestions": [{"recipe_id": "uuid", "recipe_name": "name"}]}'
    )
    user_message = (
        f"Meal slot: {payload.date} {payload.meal_type}{current_info}\n"
        f"Recipe library: {json.dumps(recipe_list, separators=(',', ':'))}\n"
        "Suggest 2-3 different recipes (exclude the current one)."
    )

    response = await call_ai(
        session,
        str(user.household_id),
        str(user.id),
        AIRequest(
            task_type="meal_planning",
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=1024,
        ),
    )

    # Parse suggestions
    cleaned = response.content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()

    try:
        data = json.loads(cleaned)
        suggestions_data = data.get("suggestions", [])
    except json.JSONDecodeError:
        logger.warning("AI swap response is not valid JSON: %r", response.content[:200])
        suggestions_data = []

    suggestions: list[SwapSuggestion] = []
    for s in suggestions_data[:3]:
        rid = s.get("recipe_id", "")
        if rid not in recipe_lookup:
            logger.warning("AI swap hallucinated recipe_id %r, skipping", rid)
            continue
        recipe = recipe_lookup[rid]
        suggestions.append(SwapSuggestion(
            recipe_id=recipe.id,
            recipe_name=recipe.name or "",
            recipe_slug=recipe.slug or "",
            categories=[c.name for c in (recipe.recipe_category or []) if hasattr(c, "name")],
            servings=int(recipe.recipe_servings) if recipe.recipe_servings else None,
        ))

    return SwapMealResponse(suggestions=suggestions)
