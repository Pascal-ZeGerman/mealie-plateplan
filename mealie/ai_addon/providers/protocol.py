"""Provider abstraction layer for AI API calls.

Use Python Protocol (structural typing) over ABC to match Mealie's duck-typing style.
All Phase 4+ code calls AIProvider — never imports anthropic or openai directly.
"""
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class AIRequest:
    task_type: str           # "meal_planning", "ingredient_parsing", etc.
    system_prompt: str
    user_message: str
    max_tokens: int = 2048


@dataclass
class AIResponse:
    content: str
    provider: str            # "claude" | "openai"
    model: str               # actual model ID used (e.g. "claude-sonnet-4-6")
    input_tokens: int
    output_tokens: int
    cost_usd: float          # pre-calculated at call time for simple budget SUM queries


@runtime_checkable
class AIProvider(Protocol):
    """Structural protocol that all provider implementations must satisfy.

    Implementations: AnthropicProvider, OpenAIProvider.
    Create client per-call with the resolved api_key (NOT at init time).
    """
    async def call(self, request: AIRequest, api_key: str) -> AIResponse: ...
    async def validate_key(self, api_key: str) -> bool: ...
