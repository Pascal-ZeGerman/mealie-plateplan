"""Task configuration routes.

GET /ai/task-config: read-only view for all authenticated users.
  Shows which provider tier is configured per task type.
  Non-admins see this as transparency info.

PUT /ai/admin/task-config: admin-only. Set provider tier for a task type.
DELETE /ai/admin/task-config/{task_type}: admin-only. Remove a task type config.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonTaskConfig
from mealie.ai_addon.providers.registry import MODEL_REGISTRY, list_tiers
from mealie.ai_addon.schema.provider import TaskConfigEntry, TaskConfigListResponse
from mealie.core.dependencies.dependencies import get_admin_user, get_current_user
from mealie.db.db_setup import generate_session
from mealie.schema.user import PrivateUser

router = APIRouter()


@router.get("/task-config", response_model=TaskConfigListResponse)
def get_task_config(
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> TaskConfigListResponse:
    """Return server-wide task routing config. Visible to all authenticated users."""
    configs = session.query(AiAddonTaskConfig).all()
    return TaskConfigListResponse(
        configs=[TaskConfigEntry(task_type=c.task_type, provider_tier=c.provider_tier) for c in configs],
        available_tiers=list_tiers(),
    )


@router.put("/admin/task-config", response_model=TaskConfigEntry)
def upsert_task_config(
    payload: TaskConfigEntry,
    current_user: PrivateUser = Depends(get_admin_user),
    session: Session = Depends(generate_session),
) -> TaskConfigEntry:
    """Set provider tier for a task type. Admin only. Upserts (create or update)."""
    if payload.provider_tier not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider_tier '{payload.provider_tier}'. Valid: {list(MODEL_REGISTRY.keys())}",
        )

    config = session.query(AiAddonTaskConfig).filter_by(task_type=payload.task_type).first()
    if config:
        config.provider_tier = payload.provider_tier
    else:
        config = AiAddonTaskConfig(task_type=payload.task_type, provider_tier=payload.provider_tier)
        session.add(config)

    session.commit()
    session.refresh(config)
    return TaskConfigEntry(task_type=config.task_type, provider_tier=config.provider_tier)


@router.delete("/admin/task-config/{task_type}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_config(
    task_type: str,
    current_user: PrivateUser = Depends(get_admin_user),
    session: Session = Depends(generate_session),
) -> None:
    """Remove a task type routing config. Admin only."""
    config = session.query(AiAddonTaskConfig).filter_by(task_type=task_type).first()
    if config:
        session.delete(config)
        session.commit()
