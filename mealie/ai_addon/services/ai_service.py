"""AI service orchestrator.

Sequence for every AI call:
1. Resolve task_type -> provider tier from AiAddonTaskConfig (DB) or default
2. Resolve api_key via key_resolver
3. Pre-flight budget check (raises 429 if >= 95%)
4. Instantiate provider and call (async)
5. Log result synchronously

ANTI-PATTERNS (do not do):
- Never call asyncio.run() inside this service — caller is already async
- Never import anthropic or openai outside providers/ layer
- Never log the api_key variable
"""
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonTaskConfig
from mealie.ai_addon.providers.anthropic_provider import AnthropicProvider
from mealie.ai_addon.providers.openai_provider import OpenAIProvider
from mealie.ai_addon.providers.protocol import AIRequest, AIResponse
from mealie.ai_addon.providers.registry import get_provider_for_tier
from mealie.ai_addon.services.budget_service import check_and_get_budget_status, log_ai_request
from mealie.ai_addon.services.key_resolver import resolve_api_key

DEFAULT_TIER = "sonnet"

_PROVIDERS = {
    "claude": AnthropicProvider(),
    "openai": OpenAIProvider(),
}


def _resolve_tier(session: Session, task_type: str) -> str:
    """Lookup task_type in AiAddonTaskConfig. Returns DEFAULT_TIER if not configured."""
    config = session.query(AiAddonTaskConfig).filter_by(task_type=task_type).first()
    return config.provider_tier if config else DEFAULT_TIER


async def call_ai(
    session: Session,
    household_id: str,
    user_id: str,
    request: AIRequest,
) -> AIResponse:
    """Main entry point for all AI calls. Called from async route handlers via await.

    Raises:
        HTTPException(400): No API key configured
        HTTPException(429): Budget exhausted
        HTTPException(500): Provider call failed (re-raised generically — key not exposed)
    """
    # 1. Resolve tier and provider
    tier = _resolve_tier(session, request.task_type)
    provider_name = get_provider_for_tier(tier)
    provider = _PROVIDERS[provider_name]

    # Attach resolved tier to request (providers read this to pick model_id)
    request._resolved_tier = tier  # type: ignore[attr-defined]

    # 2. Resolve API key (raises 400 if not configured)
    api_key = resolve_api_key(session, household_id, provider_name)

    # 3. Pre-flight budget check (raises 429 if >= 95%)
    check_and_get_budget_status(session, household_id)

    # 4. Call provider (async — NEVER wrap in asyncio.run())
    try:
        response = await provider.call(request, api_key)
    except Exception as exc:
        # Re-raise generically — do NOT include exc message (may contain API key)
        raise Exception("AI provider call failed. Check your API key and try again.") from exc

    # 5. Log result (synchronous DB write)
    log_ai_request(
        session=session,
        household_id=household_id,
        user_id=user_id,
        task_type=request.task_type,
        provider=response.provider,
        model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_usd=response.cost_usd,
    )

    return response
