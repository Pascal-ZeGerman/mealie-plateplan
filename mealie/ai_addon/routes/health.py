from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from mealie.ai_addon import ADDON_VERSION
from mealie.ai_addon.db.models import AiAddonConfig
from mealie.ai_addon.schema.addon import AddonHealthResponse
from mealie.db.db_setup import generate_session

router = APIRouter()


@router.get("/health", response_model=AddonHealthResponse)
def health(session: Session = Depends(generate_session)) -> AddonHealthResponse:
    """Return the health status of the AI addon.

    Checks:
    - DB connectivity via SELECT 1
    - Addon tables exist (query AiAddonConfig)
    - Config summary (household count, addon version)

    The mealie_api_ok field is always True when called from within the same
    process (the addon and Mealie share the same FastAPI app).
    """
    database_ok = False
    config_summary: dict = {}

    try:
        # Check basic DB connectivity
        session.execute(text("SELECT 1"))

        # Check addon table exists and is queryable
        household_count = session.execute(
            func.count(AiAddonConfig.id)  # type: ignore[call-overload]
        ).scalar()

        database_ok = True
        config_summary = {
            "addon_version": ADDON_VERSION,
            "configured_households": household_count or 0,
        }
    except Exception:
        database_ok = False

    status = "healthy" if database_ok else "degraded"

    return AddonHealthResponse(
        status=status,
        addon_version=ADDON_VERSION,
        database_ok=database_ok,
        mealie_api_ok=True,
        config_summary=config_summary,
    )
