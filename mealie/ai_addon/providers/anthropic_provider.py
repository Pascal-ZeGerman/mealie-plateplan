"""AnthropicProvider: wraps AsyncAnthropic client.

Client created per-call with the resolved api_key so household keys work correctly.
Never import this module outside the providers/ layer — always use AIProvider protocol.
"""
from anthropic import AsyncAnthropic

from mealie.ai_addon.providers.protocol import AIRequest, AIResponse
from mealie.ai_addon.providers.registry import calculate_cost_usd, get_model_id_for_tier


class AnthropicProvider:
    """Implements AIProvider protocol for Claude API."""

    PROVIDER_NAME = "claude"

    async def call(self, request: AIRequest, api_key: str) -> AIResponse:
        client = AsyncAnthropic(api_key=api_key)
        # Resolve model from task_config (passed in request) or default to sonnet
        # The ai_service layer resolves task_type -> tier before calling here
        # request.model_tier is set by ai_service — we use it directly
        tier = getattr(request, "_resolved_tier", "sonnet")
        model_id = get_model_id_for_tier(tier)

        message = await client.messages.create(
            model=model_id,
            max_tokens=request.max_tokens,
            system=request.system_prompt,
            messages=[{"role": "user", "content": request.user_message}],
        )
        input_tok = message.usage.input_tokens
        output_tok = message.usage.output_tokens
        cost = calculate_cost_usd(tier, input_tok, output_tok)

        return AIResponse(
            content=message.content[0].text,
            provider=self.PROVIDER_NAME,
            model=model_id,
            input_tokens=input_tok,
            output_tokens=output_tok,
            cost_usd=cost,
        )

    async def validate_key(self, api_key: str) -> bool:
        """Lightweight validation — count tokens on a minimal message.

        Never logs or re-raises the api_key in exception messages (key exposure risk).
        """
        try:
            client = AsyncAnthropic(api_key=api_key)
            await client.messages.count_tokens(
                model="claude-haiku-4-5-20251001",
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        except Exception:
            return False
