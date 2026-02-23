from fastapi import APIRouter

from . import admin, health, preferences, seed_ratings, status

router = APIRouter(prefix="/ai", tags=["AI Addon"])
router.include_router(health.router)
router.include_router(status.router)
router.include_router(admin.router)
router.include_router(preferences.router)
router.include_router(seed_ratings.router)
