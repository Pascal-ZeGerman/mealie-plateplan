from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonConfig
from mealie.ai_addon.schema.addon import AddonConfigOut, AddonConfigToggle, AddonStatusResponse
from mealie.core.dependencies.dependencies import get_admin_user
from mealie.db.db_setup import generate_session
from mealie.schema.user import PrivateUser

router = APIRouter(prefix="/admin")


@router.get("/config", response_model=list[AddonConfigOut])
def get_admin_config(
    current_user: PrivateUser = Depends(get_admin_user),
    session: Session = Depends(generate_session),
) -> list[AddonConfigOut]:
    """Return addon configuration records visible to the current admin.

    Super-admins see all household configs. Regular admins see only the
    config for their own household.
    """
    configs: list[AiAddonConfig]

    if current_user.admin:
        # Return all configs for this household only (group-scoped admin)
        configs = (
            session.query(AiAddonConfig)
            .filter_by(household_id=str(current_user.householdId))
            .all()
        )
    else:
        configs = []

    return [AddonConfigOut.model_validate(c) for c in configs]


@router.put("/config/{config_id}/toggle", response_model=AddonStatusResponse)
def toggle_addon_config(
    config_id: int,
    current_user: PrivateUser = Depends(get_admin_user),
    session: Session = Depends(generate_session),
) -> AddonStatusResponse:
    """Toggle the enabled flag on an addon config record.

    Only admins may call this. The config record must belong to the admin's
    household to prevent cross-household tampering.
    """
    config = session.query(AiAddonConfig).filter_by(id=config_id).first()

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Addon config with id={config_id} not found.",
        )

    # Ensure admin can only toggle their own household's config
    if str(config.household_id) != str(current_user.householdId):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this household's config.",
        )

    config.enabled = not config.enabled
    session.commit()
    session.refresh(config)

    return AddonStatusResponse(enabled=config.enabled)


@router.post("/config", response_model=AddonConfigOut, status_code=status.HTTP_201_CREATED)
def create_addon_config(
    current_user: PrivateUser = Depends(get_admin_user),
    session: Session = Depends(generate_session),
) -> AddonConfigOut:
    """Create a new addon config record for the admin's household.

    This allows admins to create an explicit config record so they can
    toggle the addon on/off via the toggle endpoint.
    """
    # Check if a config already exists for this household
    existing = session.query(AiAddonConfig).filter_by(
        household_id=str(current_user.householdId)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An addon config already exists for this household.",
        )

    new_config = AiAddonConfig(
        group_id=str(current_user.groupId),
        household_id=str(current_user.householdId),
        enabled=True,
    )
    session.add(new_config)
    session.commit()
    session.refresh(new_config)

    return AddonConfigOut.model_validate(new_config)
