"""API v1 router — aggregates all route modules."""

from fastapi import APIRouter

from app.api.v1 import health, seed

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(seed.router, tags=["seed"])
