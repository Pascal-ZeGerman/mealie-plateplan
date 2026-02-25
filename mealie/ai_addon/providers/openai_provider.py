"""OpenAIProvider: wraps AsyncOpenAI client (openai==2.21.0 — v2 API).

Client created per-call. Uses v2 API: client.chat.completions.create().
Never use openai.ChatCompletion.create() — that is the deprecated v1 API.
Never import this module outside the providers/ layer.
"""
from openai import AsyncOpenAI

from mealie.ai_addon.providers.protocol import AIRequest, AIResponse
from mealie.ai_addon.providers.registry import calculate_cost_usd, get_model_id_for_tier


class OpenAIProvider:
    """Implements AIProvider protocol for OpenAI API."""

    PROVIDER_NAME = "openai"

    async def call(self, request: AIRequest, api_key: str) -> AIResponse:
        client = AsyncOpenAI(api_key=api_key)
        tier = getattr(request, "_resolved_tier", "gpt-4o-mini")
        model_id = get_model_id_for_tier(tier)

        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ],
            max_tokens=request.max_tokens,
        )
        input_tok = response.usage.prompt_tokens
        output_tok = response.usage.completion_tokens
        cost = calculate_cost_usd(tier, input_tok, output_tok)

        return AIResponse(
            content=response.choices[0].message.content,
            provider=self.PROVIDER_NAME,
            model=model_id,
            input_tokens=input_tok,
            output_tokens=output_tok,
            cost_usd=cost,
        )

    async def validate_key(self, api_key: str) -> bool:
        """Lightweight validation — list models (fast, free).

        Never logs or re-raises the api_key in exception messages.
        """
        try:
            client = AsyncOpenAI(api_key=api_key)
            await client.models.list()
            return True
        except Exception:
            return False
