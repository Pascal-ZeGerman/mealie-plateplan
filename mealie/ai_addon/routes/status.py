from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonConfig
from mealie.ai_addon.schema.addon import AddonStatusResponse
from mealie.db.db_setup import generate_session

router = APIRouter()


@router.get("/status", response_model=AddonStatusResponse)
def get_addon_status(
    household_id: str | None = Query(None),
    session: Session = Depends(generate_session),
) -> AddonStatusResponse:
    """Return whether the AI addon is enabled for the given household.

    This is a lightweight public endpoint called by the frontend sidebar on
    every page load to conditionally show or hide the Meal Planner navigation
    entry.

    - If no household_id is provided, returns enabled=True (default state).
    - If household_id is provided and a config record exists with enabled=False,
      returns enabled=False.
    - If no config record exists for the household, defaults to enabled=True.
    """
    if not household_id:
        return AddonStatusResponse(enabled=True)

    config = session.query(AiAddonConfig).filter_by(household_id=household_id).first()
    if config is None:
        # No explicit config means the household hasn't disabled it
        return AddonStatusResponse(enabled=True)

    return AddonStatusResponse(enabled=config.enabled)
