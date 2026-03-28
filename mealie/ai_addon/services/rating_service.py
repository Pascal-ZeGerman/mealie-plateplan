"""Rating service for meal feedback and preference learning.

Implements:
- submit_rating(): upsert or clear a user's recipe rating
- _sync_to_mealie_rating(): write-through to Mealie's UserToRecipe table
- get_rating_history(): paginated rating history
- recalculate_preferences(): combine seed + meal ratings into LearnedPreferences
- get_cuisine_weights(): get cuisine weight data for settings display

Pattern 3 algorithm (from RESEARCH.md):
1. Build slug→id and id→name mappings from recipe_lookup
2. Collect seed ratings (translate slug→id), then meal ratings (override seed)
3. top_rated = recipe names with rating >= 4 (up to 10)
4. low_rated = recipe names with rating <= 2 (up to 10)
5. Cuisine weights: baseline from onboarding prefs, evolved with >= 3 ratings
"""
import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonMealRating, AiAddonSeedRating

logger = logging.getLogger(__name__)

# Baseline cuisine weight mapping from onboarding 3-point scale
CUISINE_BASELINE: dict[str, float] = {
    "love": 1.0,
    "neutral": 0.5,
    "dislike": 0.0,
}

# Minimum number of rated recipes in a cuisine before adjusting its weight
CUISINE_MIN_RATINGS = 3


@dataclass
class LearnedPreferences:
    """Computed preferences derived from seed + meal ratings.

    Used to inject learned data into AI prompts for improved suggestions.
    """

    top_rated_recipes: list[str] = field(default_factory=list)
    low_rated_recipes: list[str] = field(default_factory=list)
    cuisine_weights: dict[str, float] = field(default_factory=dict)


def submit_rating(
    session: Session,
    user_id: str,
    recipe_id: str,
    recipe_name: str,
    rating: int,
    group_meal_plan_id: int | None = None,
) -> None:
    """Submit or update a meal rating, or clear it if rating=0.

    Upsert semantics:
    - rating=0: delete existing row (clear rating)
    - rating>0, row exists: update rating, recipe_name, group_meal_plan_id
    - rating>0, no row: insert new row

    Also syncs to Mealie's UserToRecipe.rating for cross-system visibility.
    """
    existing = (
        session.query(AiAddonMealRating)
        .filter_by(user_id=user_id, recipe_id=recipe_id)
        .first()
    )

    if rating == 0:
        # Clear: delete the existing row if it exists
        if existing:
            session.delete(existing)
            session.commit()
        return

    if existing:
        # Update existing row
        existing.rating = rating
        existing.recipe_name = recipe_name
        existing.group_meal_plan_id = group_meal_plan_id
    else:
        # Insert new row
        new_rating = AiAddonMealRating(
            user_id=user_id,
            recipe_id=recipe_id,
            recipe_name=recipe_name,
            rating=rating,
            group_meal_plan_id=group_meal_plan_id,
        )
        session.add(new_rating)

    session.commit()

    # Sync to Mealie's UserToRecipe for cross-system visibility
    _sync_to_mealie_rating(session, user_id, recipe_id, float(rating))


def _sync_to_mealie_rating(
    session: Session,
    user_id: str,
    recipe_id: str,
    rating_value: float,
) -> None:
    """Write-through to Mealie's UserToRecipe.rating.

    This gives the rating visibility on Mealie's native recipe pages.
    Silently skips if user_id or recipe_id are not valid UUIDs (addon uses
    string IDs that may not match Mealie's GUID format in tests/previews).
    """
    try:
        uid = UUID(user_id)
        rid = UUID(recipe_id)
    except ValueError:
        # Not valid UUIDs — skip sync (e.g., test data with string IDs)
        return

    try:
        from mealie.db.models.users.user_to_recipe import UserToRecipe

        existing = (
            session.query(UserToRecipe)
            .filter_by(user_id=uid, recipe_id=rid)
            .first()
        )

        if existing:
            existing.rating = rating_value
        else:
            new_utr = UserToRecipe(
                user_id=uid,
                recipe_id=rid,
                rating=rating_value,
                is_favorite=False,
            )
            session.add(new_utr)

        session.commit()
    except Exception as e:
        # Non-fatal: Mealie sync failure should not block rating submission
        logger.warning("Failed to sync rating to Mealie UserToRecipe: %s", e)
        session.rollback()


def get_rating_history(
    session: Session,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[AiAddonMealRating], int]:
    """Get paginated rating history for a user.

    Returns (items, total_count) where items are ordered by update_at DESC.
    """
    query = (
        session.query(AiAddonMealRating)
        .filter_by(user_id=user_id)
        .order_by(AiAddonMealRating.update_at.desc().nullslast())
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return items, total


def recalculate_preferences(
    session: Session,
    user_id: str,
    prefs,
    recipe_lookup: list,
) -> LearnedPreferences:
    """Combine seed + meal ratings into a LearnedPreferences object.

    Algorithm (Pattern 3 from RESEARCH.md):
    1. Build slug→id and id→name mappings from recipe_lookup list
    2. Collect seed ratings (translate slug→id for matching)
    3. Collect meal ratings (override seed ratings for same recipe_id)
    4. top_rated = recipe names with final rating >= 4, up to 10
    5. low_rated = recipe names with final rating <= 2, up to 10
    6. Cuisine weights: baseline from cuisine_preferences, evolved if >= 3 ratings

    Args:
        session: Database session
        user_id: User ID string
        prefs: AiAddonUserPreference (or _FakePrefs) with cuisine_preferences dict
        recipe_lookup: List of recipe objects with .id, .name, .slug, .recipe_category
    """
    # Build index maps
    slug_to_id: dict[str, str] = {}
    id_to_name: dict[str, str] = {}
    # recipe_id -> list of category names (for cuisine weight computation)
    id_to_categories: dict[str, list[str]] = {}

    for r in recipe_lookup:
        rid = str(r.id)
        slug_to_id[r.slug] = rid
        id_to_name[rid] = r.name or ""
        categories = [c.name for c in (r.recipe_category or []) if hasattr(c, "name")]
        id_to_categories[rid] = categories

    # Start with seed ratings (translated from slug→id)
    combined: dict[str, int] = {}  # recipe_id -> rating

    seed_ratings = (
        session.query(AiAddonSeedRating)
        .filter_by(user_id=user_id)
        .all()
    )
    for seed in seed_ratings:
        recipe_id = slug_to_id.get(seed.recipe_slug)
        if recipe_id:
            combined[recipe_id] = seed.rating

    # Meal ratings override seed ratings for same recipe_id
    meal_ratings = (
        session.query(AiAddonMealRating)
        .filter_by(user_id=user_id)
        .all()
    )
    for meal in meal_ratings:
        combined[meal.recipe_id] = meal.rating

    # If no ratings at all, return empty
    if not combined:
        return LearnedPreferences()

    # Build top/low rated lists using recipe names
    top_rated: list[str] = []
    low_rated: list[str] = []

    for recipe_id, rating in combined.items():
        name = id_to_name.get(recipe_id, recipe_id)
        if rating >= 4:
            top_rated.append(name)
        elif rating <= 2:
            low_rated.append(name)

    # Cap at 10
    top_rated = top_rated[:10]
    low_rated = low_rated[:10]

    # Compute cuisine weights
    cuisine_weights: dict[str, float] = {}
    cuisine_prefs = prefs.cuisine_preferences if hasattr(prefs, "cuisine_preferences") else {}

    for cuisine, pref_value in cuisine_prefs.items():
        baseline = CUISINE_BASELINE.get(str(pref_value), 0.5)

        # Find recipe IDs that belong to this cuisine (case-insensitive, partial match)
        cuisine_recipe_ids: list[str] = []
        cuisine_lower = cuisine.lower()

        for recipe_id, cats in id_to_categories.items():
            if recipe_id in combined:
                for cat in cats:
                    if cuisine_lower in cat.lower():
                        cuisine_recipe_ids.append(recipe_id)
                        break

        rated_in_cuisine = [(rid, combined[rid]) for rid in cuisine_recipe_ids if rid in combined]

        if len(rated_in_cuisine) < CUISINE_MIN_RATINGS:
            # Not enough data — keep baseline weight
            cuisine_weights[cuisine] = baseline
        else:
            # Enough data — compute learned weight
            avg_rating = sum(r for _, r in rated_in_cuisine) / len(rated_in_cuisine)
            learned = avg_rating / 5.0
            weight = round(0.6 * learned + 0.4 * baseline, 3)
            cuisine_weights[cuisine] = weight

    return LearnedPreferences(
        top_rated_recipes=top_rated,
        low_rated_recipes=low_rated,
        cuisine_weights=cuisine_weights,
    )


def get_cuisine_weights(
    session: Session,
    user_id: str,
    prefs,
    recipe_lookup: list,
) -> list[dict]:
    """Get cuisine weight data for display on settings page.

    Returns list of dicts with cuisine, weight, has_enough_data.
    Calls recalculate_preferences() internally.
    """
    learned = recalculate_preferences(session, user_id, prefs, recipe_lookup)
    cuisine_prefs = prefs.cuisine_preferences if hasattr(prefs, "cuisine_preferences") else {}

    result = []
    for cuisine in cuisine_prefs:
        weight = learned.cuisine_weights.get(cuisine, CUISINE_BASELINE.get(str(cuisine_prefs[cuisine]), 0.5))

        # Determine if we had enough data: need to check rating count for this cuisine
        # We use a simplified check: weight != baseline means we had enough data
        baseline = CUISINE_BASELINE.get(str(cuisine_prefs[cuisine]), 0.5)
        has_enough_data = weight != baseline

        result.append({
            "cuisine": cuisine,
            "weight": weight,
            "has_enough_data": has_enough_data,
        })

    return result
