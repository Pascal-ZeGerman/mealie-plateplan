"""Pydantic schemas for provider settings, budget, and task config routes.

All extend MealieModel for camelCase JSON (via pyhumps alias_generator).
"""
from pydantic import Field

from mealie.schema._mealie.mealie_model import MealieModel


class ProviderKeyIn(MealieModel):
    """Input for POST/PUT /ai/provider-settings — save an API key."""
    provider: str  # "claude" | "openai"
    api_key: str


class ProviderKeyStatus(MealieModel):
    """Response after saving a key — shows masked key and validation result."""
    provider: str
    masked_key: str       # e.g. "sk-ant-...abcd" (last 4 chars visible)
    is_valid: bool        # result of test-connection validation
    validation_error: str | None = None


class BudgetStatusResponse(MealieModel):
    """Budget status visible to all household members."""
    spent: float
    cap: float
    pct: float
    alert: bool           # True at >= 80% — frontend shows banner
    resets_on: str        # "Sunday at midnight"


class BudgetConfigIn(MealieModel):
    """Input for PUT /ai/budget/config — update household weekly cap (household members)."""
    weekly_cap_usd: float = Field(..., ge=0.1, le=1000.0)


class ServerCapIn(MealieModel):
    """Input for PUT /ai/admin/budget/server-cap — admin sets server-wide max cap.

    Households cannot set their weekly_cap_usd above this value.
    Set server_max_cap_usd=None to remove the server-wide cap.
    """
    server_max_cap_usd: float | None = Field(None, ge=0.1, le=10000.0)


class TaskConfigEntry(MealieModel):
    """One task type routing entry."""
    task_type: str
    provider_tier: str


class TaskConfigListResponse(MealieModel):
    """Full task routing config returned to admins and (read-only) to users."""
    configs: list[TaskConfigEntry]
    available_tiers: list[dict]  # from registry.list_tiers()
