from fastapi import APIRouter

from . import admin, budget, health, preferences, provider_settings, seed_ratings, status, task_config

router = APIRouter(prefix="/ai", tags=["AI Addon"])
router.include_router(health.router)
router.include_router(status.router)
router.include_router(admin.router)
router.include_router(preferences.router)
router.include_router(seed_ratings.router)
router.include_router(provider_settings.router)
router.include_router(budget.router)
router.include_router(budget.admin_router)  # PUT /ai/admin/budget/server-cap
router.include_router(task_config.router)
