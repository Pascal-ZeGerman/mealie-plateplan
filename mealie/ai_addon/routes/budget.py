"""Budget routes.

GET /ai/budget/status: budget status visible to all household members (not admin-only).
PUT /ai/budget/config: update household weekly cap (any household member).
PUT /ai/admin/budget/server-cap: admin-only — set the server-wide maximum cap that
    households cannot exceed. Set server_max_cap_usd=None to remove the cap.
    Implements the CONTEXT.md decision: "admin can set a server-wide maximum".
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonBudgetConfig
from mealie.ai_addon.schema.provider import BudgetConfigIn, BudgetStatusResponse, ServerCapIn
from mealie.ai_addon.services.budget_service import check_and_get_budget_status
from mealie.core.dependencies.dependencies import get_admin_user, get_current_user
from mealie.db.db_setup import generate_session
from mealie.schema.user import PrivateUser

router = APIRouter(prefix="/budget")


@router.get("/status", response_model=BudgetStatusResponse)
def get_budget_status(
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> BudgetStatusResponse:
    """Return current week's spend, cap, percentage, and alert flag.

    Visible to all household members (not admin-only per CONTEXT.md).
    Does NOT raise 429 here — read-only status check only.
    """
    # Use a try/except to suppress the 429 for the read-only status endpoint
    from mealie.ai_addon.services.budget_service import get_budget_config, get_weekly_spend, ALERT_THRESHOLD_PCT, BLOCK_THRESHOLD_PCT
    cap, server_max = get_budget_config(session, str(current_user.household_id))
    effective_cap = min(cap, server_max) if server_max is not None else cap
    spent = get_weekly_spend(session, str(current_user.household_id))
    pct = (spent / effective_cap * 100) if effective_cap > 0 else 0.0

    return BudgetStatusResponse(
        spent=round(spent, 6),
        cap=effective_cap,
        pct=round(pct, 2),
        alert=pct >= ALERT_THRESHOLD_PCT,
        resets_on="Sunday at midnight",
    )


@router.put("/config", response_model=BudgetStatusResponse)
def update_budget_config(
    payload: BudgetConfigIn,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> BudgetStatusResponse:
    """Update household weekly cap. Any household member can adjust their cap."""
    from mealie.ai_addon.services.budget_service import get_budget_config, get_weekly_spend, ALERT_THRESHOLD_PCT

    config = session.query(AiAddonBudgetConfig).filter_by(
        household_id=str(current_user.household_id)
    ).first()

    if config is None:
        config = AiAddonBudgetConfig(
            household_id=str(current_user.household_id),
            weekly_cap_usd=payload.weekly_cap_usd,
        )
        session.add(config)
    else:
        # Enforce server max if set
        if config.server_max_cap_usd is not None:
            config.weekly_cap_usd = min(payload.weekly_cap_usd, config.server_max_cap_usd)
        else:
            config.weekly_cap_usd = payload.weekly_cap_usd

    session.commit()

    cap, server_max = get_budget_config(session, str(current_user.household_id))
    effective_cap = min(cap, server_max) if server_max is not None else cap
    spent = get_weekly_spend(session, str(current_user.household_id))
    pct = (spent / effective_cap * 100) if effective_cap > 0 else 0.0

    return BudgetStatusResponse(
        spent=round(spent, 6),
        cap=effective_cap,
        pct=round(pct, 2),
        alert=pct >= ALERT_THRESHOLD_PCT,
        resets_on="Sunday at midnight",
    )


admin_router = APIRouter(prefix="/admin/budget")


@admin_router.put("/server-cap", response_model=BudgetStatusResponse)
def set_server_cap(
    payload: ServerCapIn,
    current_user: PrivateUser = Depends(get_admin_user),
    session: Session = Depends(generate_session),
) -> BudgetStatusResponse:
    """Set the server-wide maximum budget cap. Admin only.

    Implements CONTEXT.md: "admin can set a server-wide maximum that households cannot exceed".
    Setting server_max_cap_usd=None removes the server cap.
    Any household whose weekly_cap_usd exceeds the new server cap is silently capped at
    server_max_cap_usd at query time (via the effective_cap calculation in budget_service).
    This route writes the server_max_cap_usd on the admin's own household record as the
    server-wide sentinel row — only one row is needed since the value is server-wide.

    NOTE: server_max_cap_usd is stored on each AiAddonBudgetConfig row but enforced globally.
    A future phase may move this to a singleton AppSettings table. For now, the admin household
    row acts as the server cap source. The get_budget_config() function already reads and
    enforces it per-household via the effective_cap calculation.
    """
    from mealie.ai_addon.services.budget_service import get_budget_config, get_weekly_spend, ALERT_THRESHOLD_PCT

    # Update server_max_cap_usd on ALL budget config rows to enforce server-wide cap
    session.query(AiAddonBudgetConfig).update(
        {"server_max_cap_usd": payload.server_max_cap_usd}
    )
    session.commit()

    # Return admin's own budget status as confirmation
    cap, server_max = get_budget_config(session, str(current_user.household_id))
    effective_cap = min(cap, server_max) if server_max is not None else cap
    spent = get_weekly_spend(session, str(current_user.household_id))
    pct = (spent / effective_cap * 100) if effective_cap > 0 else 0.0

    return BudgetStatusResponse(
        spent=round(spent, 6),
        cap=effective_cap,
        pct=round(pct, 2),
        alert=pct >= ALERT_THRESHOLD_PCT,
        resets_on="Sunday at midnight",
    )
