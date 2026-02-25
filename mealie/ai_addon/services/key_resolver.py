"""Key resolution: household key -> server env var fallback -> error.

Resolution order for each provider:
1. Query ai_addon_provider_settings for household's key.
2. If household_key_priority=True (default): use household key when found.
   If household_key_priority=False: server env var key takes precedence.
3. Fallback for OpenAI only: AppSettings.OPENAI_API_KEY env var.
4. If neither found: raise HTTPException(400, "No AI provider configured...")

SECURITY: Never log the api_key variable. Mask in UI (last 4 chars only).
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonProviderSettings
from mealie.core.config import get_app_settings


def resolve_api_key(session: Session, household_id: str, provider: str) -> str:
    """Return the API key to use for the given household and provider.

    Raises HTTPException(400) if no key is available.
    """
    settings = get_app_settings()
    record = session.query(AiAddonProviderSettings).filter_by(
        household_id=household_id,
        provider=provider,
    ).first()

    # Determine priority from the record (default: household key first)
    household_key_priority = record.household_key_priority if record else True

    if household_key_priority:
        # Household key takes priority
        if record and record.api_key:
            return record.api_key
        # Fall back to server env var (OpenAI only)
        if provider == "openai" and getattr(settings, "OPENAI_API_KEY", None):
            return settings.OPENAI_API_KEY
    else:
        # Server env var takes priority (OpenAI only)
        if provider == "openai" and getattr(settings, "OPENAI_API_KEY", None):
            return settings.OPENAI_API_KEY
        # Fall back to household key
        if record and record.api_key:
            return record.api_key

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No AI provider configured. Set up an API key in settings.",
    )
