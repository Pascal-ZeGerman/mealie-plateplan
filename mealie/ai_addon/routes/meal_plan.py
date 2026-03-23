"""Meal plan generation and management routes.

Endpoints:
  POST /ai/meal-plan/generate    — Generate a meal plan preview (not committed)
  POST /ai/meal-plan/commit      — Commit preview to Mealie's group_meal_plans table
  GET  /ai/meal-plan             — Get current week's meal plan with addon metadata
  POST /ai/meal-plan/swap        — Get AI alternative suggestions for a meal slot
  PUT  /ai/meal-plan/metadata/{plan_id} — Update lock/dining-out status for an entry

All routes require authentication (get_current_user dependency).
Service calls are async — all handlers use async def.
"""
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonMealPlanMetadata
from mealie.ai_addon.schema.meal_plan import (
    CommitMealPlanRequest,
    GenerateMealPlanRequest,
    MealPlanPreviewResponse,
    MetadataResponse,
    MetadataUpdate,
    SwapMealRequest,
    SwapMealResponse,
)
from mealie.ai_addon.services import meal_plan_service
from mealie.core.dependencies.dependencies import get_current_user
from mealie.db.db_setup import generate_session
from mealie.schema.user import PrivateUser

router = APIRouter(prefix="/meal-plan")


@router.post("/generate", response_model=MealPlanPreviewResponse)
async def generate(
    payload: GenerateMealPlanRequest,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> MealPlanPreviewResponse:
    """Generate a meal plan preview (not committed to Mealie yet).

    Returns 7 days of breakfast/lunch/dinner slots populated from the user's
    recipe library, with allergy/dietary hard constraints and cuisine soft preferences.
    Locked slots from previous commits are preserved verbatim.
    """
    return await meal_plan_service.generate_meal_plan(session, current_user, payload)


@router.post("/commit", response_model=list[int])
async def commit(
    payload: CommitMealPlanRequest,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> list[int]:
    """Commit a previewed meal plan to Mealie's group_meal_plans table.

    Creates entries in group_meal_plans and corresponding AiAddonMealPlanMetadata rows.
    Returns list of created meal plan entry IDs.
    """
    return await meal_plan_service.commit_meal_plan(session, current_user, payload)


@router.get("", response_model=MealPlanPreviewResponse)
async def get_week(
    week_start: str,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> MealPlanPreviewResponse:
    """Get current week's meal plan with addon metadata (lock/dining-out flags).

    Query param: week_start in "YYYY-MM-DD" format.
    """
    try:
        ws = date_type.fromisoformat(week_start)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid week_start format: {week_start!r}. Expected YYYY-MM-DD.")
    return await meal_plan_service.get_week_plan(session, current_user, ws)


@router.post("/swap", response_model=SwapMealResponse)
async def swap(
    payload: SwapMealRequest,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> SwapMealResponse:
    """Get 2-3 AI-suggested alternative recipes for a meal slot.

    Useful when the user wants a different suggestion for a specific slot
    without regenerating the entire week.
    """
    return await meal_plan_service.swap_meal(session, current_user, payload)


@router.put("/metadata/{plan_id}", response_model=MetadataResponse)
async def update_metadata(
    plan_id: int,
    payload: MetadataUpdate,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> MetadataResponse:
    """Update lock/dining-out status for a meal plan entry.

    Locked entries are preserved during regeneration (PLAN-04).
    Dining-out entries display with no recipe and title='Dining Out' (PLAN-05).
    """
    meta = session.query(AiAddonMealPlanMetadata).filter_by(
        group_meal_plan_id=plan_id,
        household_id=str(current_user.household_id),
    ).first()

    if not meta:
        raise HTTPException(status_code=404, detail="Metadata not found for this plan entry")

    if payload.is_locked is not None:
        meta.is_locked = payload.is_locked
    if payload.is_dining_out is not None:
        meta.is_dining_out = payload.is_dining_out

    session.commit()
    session.refresh(meta)

    return MetadataResponse(
        id=meta.id,
        group_meal_plan_id=meta.group_meal_plan_id,
        is_locked=meta.is_locked,
        is_dining_out=meta.is_dining_out,
        ai_generated=meta.ai_generated,
        week_start=meta.week_start,
    )
