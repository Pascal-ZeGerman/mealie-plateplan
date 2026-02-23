from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonUserPreference
from mealie.ai_addon.schema.preferences import PreferencesResponse, PreferencesUpdate
from mealie.core.dependencies.dependencies import get_current_user
from mealie.db.db_setup import generate_session
from mealie.schema.user import PrivateUser

router = APIRouter(prefix="/preferences")


def _get_or_create_prefs(
    session: Session,
    user: PrivateUser,
) -> AiAddonUserPreference:
    """Fetch the preference record for the current user, creating one if absent.

    The new record is flushed (not committed) so the caller can commit after
    making additional changes.
    """
    prefs = session.query(AiAddonUserPreference).filter_by(user_id=str(user.id)).first()
    if prefs is None:
        prefs = AiAddonUserPreference(
            user_id=str(user.id),
            household_id=str(user.householdId),
        )
        session.add(prefs)
        session.flush()
    return prefs


@router.get("", response_model=PreferencesResponse)
def get_preferences(
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> PreferencesResponse:
    """Return full preference state for the authenticated user.

    Creates a preference record with sensible defaults if none exists:
    empty cuisines, no allergies/restrictions, 2 adults, onboarding_complete=false.
    """
    prefs = _get_or_create_prefs(session, current_user)
    session.commit()
    return PreferencesResponse(
        cuisine_preferences=prefs.cuisine_preferences,
        allergies=prefs.allergies,
        dietary_restrictions=prefs.dietary_restrictions,
        family_adults=prefs.family_adults,
        family_teens=prefs.family_teens,
        family_children=prefs.family_children,
        family_toddlers=prefs.family_toddlers,
        calculated_portions=prefs.calculated_portions,
        portion_override=prefs.portion_override,
        effective_portions=prefs.effective_portions,
        onboarding_complete=prefs.onboarding_complete,
    )


@router.put("", response_model=PreferencesResponse)
def update_preferences(
    payload: PreferencesUpdate,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> PreferencesResponse:
    """Accept partial preference updates and persist to the database.

    Only fields present in the payload (non-None) are updated. This supports
    per-step auto-save where each wizard step only sends its own fields.
    """
    prefs = _get_or_create_prefs(session, current_user)

    if payload.cuisine_preferences is not None:
        # Convert enum values to plain strings before storing as JSON
        prefs.cuisine_preferences = {k: v.value for k, v in payload.cuisine_preferences.items()}
    if payload.allergies is not None:
        prefs.allergies = payload.allergies
    if payload.dietary_restrictions is not None:
        prefs.dietary_restrictions = payload.dietary_restrictions
    if payload.family_adults is not None:
        prefs.family_adults = payload.family_adults
    if payload.family_teens is not None:
        prefs.family_teens = payload.family_teens
    if payload.family_children is not None:
        prefs.family_children = payload.family_children
    if payload.family_toddlers is not None:
        prefs.family_toddlers = payload.family_toddlers
    if payload.portion_override is not None:
        prefs.portion_override = payload.portion_override
    if payload.onboarding_complete is not None:
        prefs.onboarding_complete = payload.onboarding_complete

    session.commit()
    session.refresh(prefs)

    return PreferencesResponse(
        cuisine_preferences=prefs.cuisine_preferences,
        allergies=prefs.allergies,
        dietary_restrictions=prefs.dietary_restrictions,
        family_adults=prefs.family_adults,
        family_teens=prefs.family_teens,
        family_children=prefs.family_children,
        family_toddlers=prefs.family_toddlers,
        calculated_portions=prefs.calculated_portions,
        portion_override=prefs.portion_override,
        effective_portions=prefs.effective_portions,
        onboarding_complete=prefs.onboarding_complete,
    )
