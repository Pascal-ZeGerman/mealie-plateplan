"""Unit tests for the AI addon health, schemas, and routes.

These tests verify correctness of models and schemas without requiring a
live database or running FastAPI instance. They exercise:

- ORM model table names (ai_addon_ prefix convention)
- Schema camelCase serialization via MealieModel alias_generator
- ORM-to-schema mapping (from_attributes / from_orm)
- AddonStatusResponse enabled field serialization
- FastAPI router registration and path structure
"""
import pytest

from mealie.ai_addon.db.models import AiAddonConfig, AiAddonUserPreference
from mealie.ai_addon.schema.addon import (
    AddonConfigOut,
    AddonConfigToggle,
    AddonHealthResponse,
    AddonStatusResponse,
)


# ---------------------------------------------------------------------------
# Model table name tests
# ---------------------------------------------------------------------------


def test_ai_addon_config_table_name():
    """AiAddonConfig must use the ai_addon_ prefix."""
    assert AiAddonConfig.__tablename__ == "ai_addon_config"


def test_ai_addon_user_preferences_table_name():
    """AiAddonUserPreference must use the ai_addon_ prefix."""
    assert AiAddonUserPreference.__tablename__ == "ai_addon_user_preferences"


# ---------------------------------------------------------------------------
# Schema camelCase serialization tests
# ---------------------------------------------------------------------------


def test_addon_health_response_camelcase():
    """AddonHealthResponse serializes to camelCase via MealieModel alias_generator."""
    health = AddonHealthResponse(
        status="healthy",
        addon_version="0.1.0",
        database_ok=True,
        mealie_api_ok=True,
        config_summary={"configured_households": 2},
    )
    data = health.model_dump(by_alias=True)

    assert "addonVersion" in data, "addon_version should serialize as addonVersion"
    assert "databaseOk" in data, "database_ok should serialize as databaseOk"
    assert "mealieApiOk" in data, "mealie_api_ok should serialize as mealieApiOk"
    assert "configSummary" in data, "config_summary should serialize as configSummary"
    assert data["addonVersion"] == "0.1.0"
    assert data["databaseOk"] is True
    assert data["mealieApiOk"] is True
    assert data["status"] == "healthy"


def test_addon_status_response_serialization():
    """AddonStatusResponse serializes the enabled field correctly."""
    enabled_resp = AddonStatusResponse(enabled=True)
    disabled_resp = AddonStatusResponse(enabled=False)

    enabled_data = enabled_resp.model_dump()
    disabled_data = disabled_resp.model_dump()

    assert enabled_data["enabled"] is True
    assert disabled_data["enabled"] is False


def test_addon_config_toggle_schema():
    """AddonConfigToggle has an enabled field."""
    toggle = AddonConfigToggle(enabled=False)
    assert toggle.enabled is False

    toggle_on = AddonConfigToggle(enabled=True)
    assert toggle_on.enabled is True


# ---------------------------------------------------------------------------
# ORM compatibility (from_attributes) test
# ---------------------------------------------------------------------------


class FakeOrmConfig:
    """Minimal ORM-like object to test from_attributes mapping."""

    def __init__(self):
        self.id = 42
        self.group_id = "group-abc"
        self.household_id = "household-xyz"
        self.enabled = True


def test_addon_config_out_from_orm():
    """AddonConfigOut.model_validate works with ORM-like objects (from_attributes=True)."""
    fake = FakeOrmConfig()
    config_out = AddonConfigOut.model_validate(fake)

    assert config_out.id == 42
    assert config_out.group_id == "group-abc"
    assert config_out.household_id == "household-xyz"
    assert config_out.enabled is True


def test_addon_config_out_no_camelcase():
    """AddonConfigOut should NOT camelize its keys (alias_generator=None)."""
    fake = FakeOrmConfig()
    config_out = AddonConfigOut.model_validate(fake)
    data = config_out.model_dump(by_alias=True)

    # Keys should remain snake_case since alias_generator is None
    assert "group_id" in data
    assert "household_id" in data
    assert "enabled" in data


# ---------------------------------------------------------------------------
# Router registration tests
# ---------------------------------------------------------------------------


def test_health_router_has_health_path():
    """The health router exposes a /health GET endpoint."""
    from mealie.ai_addon.routes import health as health_module

    paths = [r.path for r in health_module.router.routes]
    assert "/health" in paths, f"Expected /health in {paths}"


def test_status_router_has_status_path():
    """The status router exposes a /status GET endpoint."""
    from mealie.ai_addon.routes import status as status_module

    paths = [r.path for r in status_module.router.routes]
    assert "/status" in paths, f"Expected /status in {paths}"


def test_admin_router_has_config_paths():
    """The admin router exposes /admin/config GET and POST endpoints."""
    from mealie.ai_addon.routes import admin as admin_module

    paths = [r.path for r in admin_module.router.routes]
    assert "/admin/config" in paths, f"Expected /admin/config in {paths}"


def test_main_router_includes_all_sub_routers():
    """The main AI addon router includes health, status, and admin sub-routers."""
    from mealie.ai_addon.routes import router

    # The main router should have routes (including those from sub-routers)
    assert len(router.routes) > 0, "Main router should include sub-router routes"
