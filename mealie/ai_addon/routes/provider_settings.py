"""Provider settings routes — API key management.

POST /ai/provider-settings: save a key (any household member; not admin-gated).
  - Validate key via provider.validate_key() before persisting (test-on-save).
  - Upsert: create or update the record for (household_id, provider).
  - Return masked key and validation result.
  - NEVER log or return the raw api_key.

DELETE /ai/provider-settings/{provider}: remove a key.
GET /ai/provider-settings: list providers with masked keys (shows "configured" status).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonProviderSettings
from mealie.ai_addon.providers.anthropic_provider import AnthropicProvider
from mealie.ai_addon.providers.openai_provider import OpenAIProvider
from mealie.ai_addon.schema.provider import ProviderKeyIn, ProviderKeyStatus
from mealie.core.dependencies.dependencies import get_current_user
from mealie.db.db_setup import generate_session
from mealie.schema.user import PrivateUser

router = APIRouter(prefix="/provider-settings")

_VALIDATORS = {
    "claude": AnthropicProvider(),
    "openai": OpenAIProvider(),
}

SUPPORTED_PROVIDERS = {"claude", "openai"}


@router.get("", response_model=list[ProviderKeyStatus])
async def list_provider_settings(
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> list[ProviderKeyStatus]:
    """Return configured providers with masked keys (last 4 chars visible)."""
    records = session.query(AiAddonProviderSettings).filter_by(
        household_id=str(current_user.householdId)
    ).all()
    result = []
    for r in records:
        masked = f"...{r.api_key[-4:]}" if len(r.api_key) >= 4 else "****"
        result.append(ProviderKeyStatus(provider=r.provider, masked_key=masked, is_valid=True))
    return result


@router.post("", response_model=ProviderKeyStatus, status_code=status.HTTP_200_OK)
async def save_provider_key(
    payload: ProviderKeyIn,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> ProviderKeyStatus:
    """Save (upsert) an API key. Validates before persisting — fails fast on bad key."""
    if payload.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{payload.provider}'. Supported: {SUPPORTED_PROVIDERS}",
        )

    validator = _VALIDATORS[payload.provider]
    is_valid = await validator.validate_key(payload.api_key)

    if not is_valid:
        masked = f"...{payload.api_key[-4:]}" if len(payload.api_key) >= 4 else "****"
        return ProviderKeyStatus(
            provider=payload.provider,
            masked_key=masked,
            is_valid=False,
            validation_error="API key validation failed. Check the key and try again.",
        )

    # Upsert
    record = session.query(AiAddonProviderSettings).filter_by(
        household_id=str(current_user.householdId),
        provider=payload.provider,
    ).first()

    if record:
        record.api_key = payload.api_key
    else:
        record = AiAddonProviderSettings(
            household_id=str(current_user.householdId),
            provider=payload.provider,
            api_key=payload.api_key,
        )
        session.add(record)

    session.commit()

    masked = f"...{payload.api_key[-4:]}" if len(payload.api_key) >= 4 else "****"
    return ProviderKeyStatus(provider=payload.provider, masked_key=masked, is_valid=True)


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider_key(
    provider: str,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> None:
    """Remove a saved API key for the given provider."""
    record = session.query(AiAddonProviderSettings).filter_by(
        household_id=str(current_user.householdId),
        provider=provider,
    ).first()
    if record:
        session.delete(record)
        session.commit()
