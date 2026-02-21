from fastapi import APIRouter

from . import health

router = APIRouter(prefix="/ai", tags=["AI Addon"])
router.include_router(health.router)
