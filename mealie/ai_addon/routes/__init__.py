from fastapi import APIRouter

from . import admin, health, status

router = APIRouter(prefix="/ai", tags=["AI Addon"])
router.include_router(health.router)
router.include_router(status.router)
router.include_router(admin.router)
