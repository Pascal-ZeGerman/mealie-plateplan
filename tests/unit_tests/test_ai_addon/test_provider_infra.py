"""Unit tests for AI provider infrastructure: models, registry, cost calculation,
services, schemas, and routes.

These tests verify correctness without requiring a live database, running FastAPI
instance, or real AI API keys. All tests are pure unit logic.
"""
import os

import pytest

# Set required env vars before any Mealie imports that touch config
os.environ.setdefault("DATA_DIR", "/tmp/mealie-test")
os.environ.setdefault("PRODUCTION", "false")


# ---------------------------------------------------------------------------
# Task 2: Model table names (new provider infra tables)
# ---------------------------------------------------------------------------


def test_new_table_names():
    """All four new provider infra model classes must have ai_addon_ prefixed tablenames."""
    from mealie.ai_addon.db.models import (
        AiAddonAiRequestLog,
        AiAddonBudgetConfig,
        AiAddonProviderSettings,
        AiAddonTaskConfig,
    )

    names = [
        AiAddonProviderSettings.__tablename__,
        AiAddonBudgetConfig.__tablename__,
        AiAddonAiRequestLog.__tablename__,
        AiAddonTaskConfig.__tablename__,
    ]
    assert all(n.startswith("ai_addon_") for n in names), f"Bad table names: {names}"
    assert AiAddonProviderSettings.__tablename__ == "ai_addon_provider_settings"
    assert AiAddonBudgetConfig.__tablename__ == "ai_addon_budget_config"
    assert AiAddonAiRequestLog.__tablename__ == "ai_addon_ai_request_log"
    assert AiAddonTaskConfig.__tablename__ == "ai_addon_task_config"


# ---------------------------------------------------------------------------
# Task 2: Cost calculation
# ---------------------------------------------------------------------------


def test_calculate_cost_usd_haiku():
    """Known token counts should produce correct cost for haiku tier.

    haiku: $1/MTok input, $5/MTok output
    1000 input tokens = 1000/1,000,000 * $1 = $0.001
    500 output tokens = 500/1,000,000 * $5 = $0.0025
    total = $0.0035
    """
    from mealie.ai_addon.providers.registry import calculate_cost_usd

    cost = calculate_cost_usd("haiku", 1000, 500)
    assert cost == pytest.approx(0.0035, rel=1e-6)


def test_calculate_cost_usd_zero_tokens():
    """Zero tokens should return 0.0 cost."""
    from mealie.ai_addon.providers.registry import calculate_cost_usd

    cost = calculate_cost_usd("haiku", 0, 0)
    assert cost == 0.0


def test_list_tiers_returns_all_five():
    """list_tiers() must return exactly 5 entries with expected tier keys."""
    from mealie.ai_addon.providers.registry import list_tiers

    tiers = list_tiers()
    assert len(tiers) == 5
    tier_names = {t["tier"] for t in tiers}
    assert tier_names == {"haiku", "sonnet", "opus", "gpt-4o-mini", "gpt-4o"}


def test_model_registry_has_required_keys():
    """Each registry entry must have provider, model_id, display_name, approx_cost_per_call."""
    from mealie.ai_addon.providers.registry import MODEL_REGISTRY

    required_keys = {"provider", "model_id", "display_name", "approx_cost_per_call"}
    for tier, meta in MODEL_REGISTRY.items():
        missing = required_keys - set(meta.keys())
        assert not missing, f"Tier '{tier}' missing keys: {missing}"


# ---------------------------------------------------------------------------
# Task 2: Protocol dataclasses
# ---------------------------------------------------------------------------


def test_airesponse_dataclass():
    """AIResponse can be constructed and fields are accessible."""
    from mealie.ai_addon.providers.protocol import AIResponse

    resp = AIResponse(
        content="Test meal plan",
        provider="claude",
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=200,
        cost_usd=0.0015,
    )
    assert resp.content == "Test meal plan"
    assert resp.provider == "claude"
    assert resp.model == "claude-sonnet-4-6"
    assert resp.input_tokens == 100
    assert resp.output_tokens == 200
    assert resp.cost_usd == pytest.approx(0.0015)


def test_airequest_dataclass():
    """AIRequest defaults max_tokens to 2048."""
    from mealie.ai_addon.providers.protocol import AIRequest

    req = AIRequest(
        task_type="meal_planning",
        system_prompt="You are a meal planner.",
        user_message="Plan my week.",
    )
    assert req.max_tokens == 2048
    assert req.task_type == "meal_planning"


def test_provider_protocol_structural():
    """AnthropicProvider and OpenAIProvider must satisfy isinstance(obj, AIProvider) check."""
    from mealie.ai_addon.providers.anthropic_provider import AnthropicProvider
    from mealie.ai_addon.providers.openai_provider import OpenAIProvider
    from mealie.ai_addon.providers.protocol import AIProvider

    anthropic_provider = AnthropicProvider()
    openai_provider = OpenAIProvider()

    assert isinstance(anthropic_provider, AIProvider), (
        "AnthropicProvider does not satisfy AIProvider protocol"
    )
    assert isinstance(openai_provider, AIProvider), (
        "OpenAIProvider does not satisfy AIProvider protocol"
    )


# ---------------------------------------------------------------------------
# Task 3a: Budget service — week boundary
# ---------------------------------------------------------------------------


def test_get_week_start_utc_is_sunday():
    """get_week_start_utc() must always return a Sunday (weekday() == 6)."""
    from mealie.ai_addon.services.budget_service import get_week_start_utc

    week_start = get_week_start_utc()
    assert week_start.weekday() == 6, (
        f"Expected Sunday (weekday=6), got weekday={week_start.weekday()} ({week_start})"
    )
    # Also verify time is midnight
    assert week_start.hour == 0
    assert week_start.minute == 0
    assert week_start.second == 0


def test_get_week_start_utc_monday():
    """Freeze time to a Monday — week_start must be the prior Sunday."""
    try:
        from freezegun import freeze_time
    except ImportError:
        pytest.skip("freezegun not installed — skipping frozen-time test")

    from mealie.ai_addon.services.budget_service import get_week_start_utc

    # 2026-02-23 is a Monday
    with freeze_time("2026-02-23 14:30:00"):
        week_start = get_week_start_utc()
        # Prior Sunday is 2026-02-22
        assert week_start.year == 2026
        assert week_start.month == 2
        assert week_start.day == 22
        assert week_start.weekday() == 6


# ---------------------------------------------------------------------------
# Task 3a: Budget service — threshold enforcement
# ---------------------------------------------------------------------------


def test_budget_status_thresholds():
    """Budget enforcement: 79% -> no alert, 80% -> alert=True, 95% -> raises 429."""
    from unittest.mock import MagicMock, patch

    from fastapi import HTTPException

    from mealie.ai_addon.services.budget_service import check_and_get_budget_status

    session = MagicMock()

    # --- 79% case: no alert ---
    with (
        patch("mealie.ai_addon.services.budget_service.get_budget_config", return_value=(10.0, None)),
        patch("mealie.ai_addon.services.budget_service.get_weekly_spend", return_value=7.9),
    ):
        result = check_and_get_budget_status(session, "hh-test")
        assert result["alert"] is False
        assert result["pct"] == pytest.approx(79.0)

    # --- 80% case: alert=True ---
    with (
        patch("mealie.ai_addon.services.budget_service.get_budget_config", return_value=(10.0, None)),
        patch("mealie.ai_addon.services.budget_service.get_weekly_spend", return_value=8.0),
    ):
        result = check_and_get_budget_status(session, "hh-test")
        assert result["alert"] is True
        assert result["pct"] == pytest.approx(80.0)

    # --- 95% case: raises HTTPException 429 ---
    with (
        patch("mealie.ai_addon.services.budget_service.get_budget_config", return_value=(10.0, None)),
        patch("mealie.ai_addon.services.budget_service.get_weekly_spend", return_value=9.5),
    ):
        with pytest.raises(HTTPException) as exc_info:
            check_and_get_budget_status(session, "hh-test")
        assert exc_info.value.status_code == 429
        assert "Weekly budget" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Task 3a: Schema camelCase serialization
# ---------------------------------------------------------------------------


def test_budget_schema_camelcase():
    """BudgetStatusResponse must serialize resets_on as resetsOn via MealieModel."""
    from mealie.ai_addon.schema.provider import BudgetStatusResponse

    resp = BudgetStatusResponse(
        spent=5.0,
        cap=10.0,
        pct=50.0,
        alert=False,
        resets_on="Sunday at midnight",
    )
    data = resp.model_dump(by_alias=True)
    assert "resetsOn" in data, f"Expected resetsOn in {list(data.keys())}"
    assert data["resetsOn"] == "Sunday at midnight"


def test_task_config_entry_camelcase():
    """TaskConfigEntry must serialize task_type as taskType, provider_tier as providerTier."""
    from mealie.ai_addon.schema.provider import TaskConfigEntry

    entry = TaskConfigEntry(task_type="meal_planning", provider_tier="sonnet")
    data = entry.model_dump(by_alias=True)
    assert "taskType" in data, f"Expected taskType in {list(data.keys())}"
    assert "providerTier" in data, f"Expected providerTier in {list(data.keys())}"
    assert data["taskType"] == "meal_planning"
    assert data["providerTier"] == "sonnet"


# ---------------------------------------------------------------------------
# Task 3b: Route registration
# ---------------------------------------------------------------------------


def test_new_routes_registered():
    """Main addon router must have paths for provider-settings, budget, admin/budget, task-config."""
    from mealie.ai_addon.routes import router

    all_paths = [r.path for r in router.routes]

    assert any("provider-settings" in p for p in all_paths), (
        f"Expected provider-settings route in {all_paths}"
    )
    assert any("budget" in p for p in all_paths), (
        f"Expected budget route in {all_paths}"
    )
    assert any("admin" in p and "budget" in p for p in all_paths), (
        f"Expected admin/budget route in {all_paths}"
    )
    assert any("task-config" in p for p in all_paths), (
        f"Expected task-config route in {all_paths}"
    )


# ---------------------------------------------------------------------------
# Registry: provider routing and additional tier cost calculation
# ---------------------------------------------------------------------------


def test_get_provider_for_tier_claude_tiers():
    """haiku, sonnet, opus all map to the 'claude' provider."""
    from mealie.ai_addon.providers.registry import get_provider_for_tier

    assert get_provider_for_tier("haiku") == "claude"
    assert get_provider_for_tier("sonnet") == "claude"
    assert get_provider_for_tier("opus") == "claude"


def test_get_provider_for_tier_openai_tiers():
    """gpt-4o-mini and gpt-4o both map to the 'openai' provider."""
    from mealie.ai_addon.providers.registry import get_provider_for_tier

    assert get_provider_for_tier("gpt-4o-mini") == "openai"
    assert get_provider_for_tier("gpt-4o") == "openai"


def test_calculate_cost_usd_sonnet():
    """Verify sonnet tier cost calculation.

    sonnet: $3/MTok input, $15/MTok output
    1000 input tokens = 1000/1,000,000 * $3 = $0.003
    500 output tokens = 500/1,000,000 * $15 = $0.0075
    total = $0.0105
    """
    from mealie.ai_addon.providers.registry import calculate_cost_usd

    cost = calculate_cost_usd("sonnet", 1000, 500)
    assert cost == pytest.approx(0.0105, rel=1e-6)


# ---------------------------------------------------------------------------
# key_resolver: resolve_api_key priority logic
# ---------------------------------------------------------------------------


def test_resolve_api_key_returns_household_key_when_found():
    """Priority=True (default), household key exists → return household key."""
    from unittest.mock import MagicMock, patch

    from mealie.ai_addon.services.key_resolver import resolve_api_key

    session = MagicMock()
    record = MagicMock()
    record.api_key = "sk-ant-household-key"
    record.household_key_priority = True
    session.query.return_value.filter_by.return_value.first.return_value = record

    with patch("mealie.ai_addon.services.key_resolver.get_app_settings"):
        result = resolve_api_key(session, "hh-123", "claude")

    assert result == "sk-ant-household-key"


def test_resolve_api_key_openai_falls_back_to_env_var():
    """Priority=True, no household key, OpenAI env var present → return env var."""
    from unittest.mock import MagicMock, patch

    from mealie.ai_addon.services.key_resolver import resolve_api_key

    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = None

    mock_settings = MagicMock()
    mock_settings.OPENAI_API_KEY = "sk-openai-env-key"

    with patch("mealie.ai_addon.services.key_resolver.get_app_settings", return_value=mock_settings):
        result = resolve_api_key(session, "hh-123", "openai")

    assert result == "sk-openai-env-key"


def test_resolve_api_key_no_key_raises_400():
    """No household key and no env var fallback → raises HTTP 400."""
    from unittest.mock import MagicMock, patch

    from fastapi import HTTPException

    from mealie.ai_addon.services.key_resolver import resolve_api_key

    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = None

    mock_settings = MagicMock(spec=[])  # no OPENAI_API_KEY attribute

    with patch("mealie.ai_addon.services.key_resolver.get_app_settings", return_value=mock_settings):
        with pytest.raises(HTTPException) as exc_info:
            resolve_api_key(session, "hh-123", "claude")

    assert exc_info.value.status_code == 400
    assert "No AI provider configured" in exc_info.value.detail


# ---------------------------------------------------------------------------
# budget_service: server_max_cap enforcement and default config
# ---------------------------------------------------------------------------


def test_budget_status_server_max_cap_lowers_effective_cap():
    """server_max_cap ($5) < household weekly_cap ($10) → effective_cap = $5."""
    from unittest.mock import patch

    from mealie.ai_addon.services.budget_service import check_and_get_budget_status

    from unittest.mock import MagicMock
    session = MagicMock()

    # Spend $4.50 of $5 server max (90%) — well above 80% alert
    with (
        patch("mealie.ai_addon.services.budget_service.get_budget_config", return_value=(10.0, 5.0)),
        patch("mealie.ai_addon.services.budget_service.get_weekly_spend", return_value=4.5),
    ):
        result = check_and_get_budget_status(session, "hh-test")

    assert result["cap"] == pytest.approx(5.0)
    assert result["pct"] == pytest.approx(90.0)
    assert result["alert"] is True


def test_budget_status_server_max_cap_above_household_cap_ignored():
    """server_max_cap ($20) > household weekly_cap ($10) → effective_cap = $10."""
    from unittest.mock import MagicMock, patch

    from mealie.ai_addon.services.budget_service import check_and_get_budget_status

    session = MagicMock()

    # Spend $5.00 of $10 household cap (50%) — no alert
    with (
        patch("mealie.ai_addon.services.budget_service.get_budget_config", return_value=(10.0, 20.0)),
        patch("mealie.ai_addon.services.budget_service.get_weekly_spend", return_value=5.0),
    ):
        result = check_and_get_budget_status(session, "hh-test")

    assert result["cap"] == pytest.approx(10.0)
    assert result["pct"] == pytest.approx(50.0)
    assert result["alert"] is False


# ---------------------------------------------------------------------------
# ai_service: _resolve_tier default and DB lookup
# ---------------------------------------------------------------------------


def test_resolve_tier_returns_configured_tier_when_found():
    """Task type found in AiAddonTaskConfig → returns its provider_tier."""
    from unittest.mock import MagicMock

    from mealie.ai_addon.services.ai_service import _resolve_tier

    session = MagicMock()
    config = MagicMock()
    config.provider_tier = "haiku"
    session.query.return_value.filter_by.return_value.first.return_value = config

    assert _resolve_tier(session, "meal_planning") == "haiku"


def test_resolve_tier_returns_default_when_not_configured():
    """Task type not in DB → returns DEFAULT_TIER ('sonnet')."""
    from unittest.mock import MagicMock

    from mealie.ai_addon.services.ai_service import DEFAULT_TIER, _resolve_tier

    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = None

    result = _resolve_tier(session, "unknown_task_type")

    assert result == DEFAULT_TIER
    assert DEFAULT_TIER == "sonnet"
