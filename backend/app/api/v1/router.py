"""API v1 router composition."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.seed import router as seed_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(seed_router)
