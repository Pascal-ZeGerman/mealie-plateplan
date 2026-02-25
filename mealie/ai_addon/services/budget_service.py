"""Budget enforcement: weekly spend tracking with 80% alert and 95% hard block.

Week boundary: Sunday 00:00:00 UTC (fixed reset, not rolling).
Budget scope: per-household; all household members share one cap.
Visibility: all household members can read budget status (not admin-only).
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonAiRequestLog, AiAddonBudgetConfig

DEFAULT_WEEKLY_CAP_USD = 10.0
ALERT_THRESHOLD_PCT = 80.0
BLOCK_THRESHOLD_PCT = 95.0


def get_week_start_utc() -> datetime:
    """Returns the most recent Sunday 00:00:00 UTC."""
    now = datetime.now(timezone.utc)
    # weekday(): Mon=0 ... Sun=6. Days since last Sunday:
    days_since_sunday = (now.weekday() + 1) % 7
    sunday = now - timedelta(days=days_since_sunday)
    return sunday.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def get_weekly_spend(session: Session, household_id: str) -> float:
    """Sum all logged AI costs since the most recent Sunday 00:00 UTC."""
    week_start = get_week_start_utc()
    # created_at is stored as naive UTC in SqlAlchemyBase — compare as naive
    week_start_naive = week_start.replace(tzinfo=None)
    result = session.query(func.sum(AiAddonAiRequestLog.cost_usd)).filter(
        AiAddonAiRequestLog.household_id == household_id,
        AiAddonAiRequestLog.created_at >= week_start_naive,
    ).scalar()
    return float(result or 0.0)


def get_budget_config(session: Session, household_id: str) -> tuple[float, float | None]:
    """Return (weekly_cap_usd, server_max_cap_usd) for the household.

    If no config record exists, returns defaults ($10, None).
    """
    config = session.query(AiAddonBudgetConfig).filter_by(
        household_id=household_id
    ).first()
    if config is None:
        return DEFAULT_WEEKLY_CAP_USD, None
    return config.weekly_cap_usd, config.server_max_cap_usd


def check_and_get_budget_status(session: Session, household_id: str) -> dict:
    """Return budget status dict. Raises HTTP 429 at >= 95% usage.

    Returns: {spent, cap, pct, alert} where alert=True at >= 80%.
    The 429 response message is shown directly to the user in the frontend.
    """
    cap, server_max = get_budget_config(session, household_id)
    # Server max cap cannot be exceeded by household cap
    effective_cap = min(cap, server_max) if server_max is not None else cap
    spent = get_weekly_spend(session, household_id)
    pct = (spent / effective_cap * 100) if effective_cap > 0 else 0.0

    if pct >= BLOCK_THRESHOLD_PCT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Weekly budget nearly exhausted. Resets Sunday at midnight.",
        )

    return {
        "spent": round(spent, 6),
        "cap": effective_cap,
        "pct": round(pct, 2),
        "alert": pct >= ALERT_THRESHOLD_PCT,
        "resets_on": "Sunday at midnight",
    }


def log_ai_request(
    session: Session,
    household_id: str,
    user_id: str,
    task_type: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> None:
    """Write an immutable log entry for an AI call. Call after a successful provider.call()."""
    from mealie.ai_addon.db.models import AiAddonAiRequestLog
    entry = AiAddonAiRequestLog(
        household_id=household_id,
        user_id=user_id,
        task_type=task_type,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )
    session.add(entry)
    session.commit()
