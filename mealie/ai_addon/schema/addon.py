from pydantic import ConfigDict

from mealie.schema._mealie.mealie_model import MealieModel


class AddonHealthResponse(MealieModel):
    """Detailed health status of the AI addon.

    Field names use snake_case here; MealieModel's alias_generator (camelize)
    produces camelCase JSON: addon_version -> addonVersion, etc.
    """

    status: str
    addon_version: str
    database_ok: bool
    mealie_api_ok: bool
    config_summary: dict


class AddonConfigOut(MealieModel):
    """Output schema for addon configuration records."""

    model_config = ConfigDict(alias_generator=None, populate_by_name=True, from_attributes=True)

    id: int
    group_id: str
    household_id: str
    enabled: bool


class AddonStatusResponse(MealieModel):
    """Lightweight status schema used by the frontend sidebar.

    The frontend checks this to conditionally show/hide the Meal Planner
    navigation entry.
    """

    enabled: bool


class AddonConfigToggle(MealieModel):
    """Input schema for admin toggle requests.

    Currently unused in favour of the toggle-by-id endpoint, but kept
    for future use where the payload may carry additional metadata.
    """

    enabled: bool
