"""Meal rating endpoints.

Endpoints:
  POST /ai/ratings               — Submit or update a meal rating (0=clear)
  GET  /ai/ratings/history       — Get paginated rating history
  GET  /ai/ratings/cuisine-weights — Get learned cuisine weight data

All routes require authentication (get_current_user dependency).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonUserPreference
from mealie.ai_addon.schema.rating import (
    CuisineWeightEntry,
    CuisineWeightsResponse,
    RatingHistoryResponse,
    RatingIn,
    RatingOut,
)
from mealie.ai_addon.services.rating_service import (
    get_cuisine_weights,
    get_rating_history,
    submit_rating,
)
from mealie.core.dependencies.dependencies import get_current_user
from mealie.db.db_setup import generate_session
from mealie.repos.all_repositories import get_repositories
from mealie.schema.response.pagination import PaginationQuery
from mealie.schema.user import PrivateUser

router = APIRouter(prefix="/ratings", tags=["AI Addon - Ratings"])


@router.post("", response_model=dict)
def submit_meal_rating(
    payload: RatingIn,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> dict:
    """Submit, update, or clear a meal rating.

    rating=0 clears the existing rating (delete).
    rating=1-5 sets or updates the rating.
    Syncs to Mealie's UserToRecipe.rating for cross-system visibility.
    """
    submit_rating(
        session,
        str(current_user.id),
        payload.recipe_id,
        payload.recipe_name,
        payload.rating,
        payload.group_meal_plan_id,
    )
    return {"status": "ok"}


@router.get("/history", response_model=RatingHistoryResponse)
def get_rating_history_endpoint(
    limit: int = 20,
    offset: int = 0,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> RatingHistoryResponse:
    """Get paginated rating history for the current user.

    Ordered by most recent first.
    """
    items, total = get_rating_history(session, str(current_user.id), limit=limit, offset=offset)
    rating_outs = [
        RatingOut(
            id=r.id,
            recipe_id=r.recipe_id,
            recipe_name=r.recipe_name,
            rating=r.rating,
            updated_at=r.update_at,
        )
        for r in items
    ]
    return RatingHistoryResponse(items=rating_outs, total=total)


@router.get("/cuisine-weights", response_model=CuisineWeightsResponse)
def get_cuisine_weights_endpoint(
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> CuisineWeightsResponse:
    """Get learned cuisine weights for display on settings page.

    Returns baseline weights if fewer than 3 ratings exist for a cuisine.
    has_enough_data=True means the weight has evolved from the baseline.
    """
    prefs = session.query(AiAddonUserPreference).filter_by(user_id=str(current_user.id)).first()

    # Fetch recipe library for cuisine category matching
    repos = get_repositories(session, group_id=current_user.group_id, household_id=current_user.household_id)
    all_recipes_result = repos.recipes.by_user(current_user.id).page_all(
        PaginationQuery(page=1, per_page=-1)
    )
    recipe_lookup = all_recipes_result.items

    weights_data = get_cuisine_weights(session, str(current_user.id), prefs, recipe_lookup)
    entries = [
        CuisineWeightEntry(
            cuisine=w["cuisine"],
            weight=w["weight"],
            has_enough_data=w["has_enough_data"],
        )
        for w in weights_data
    ]
    return CuisineWeightsResponse(weights=entries)
