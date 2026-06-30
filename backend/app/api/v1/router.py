from fastapi import APIRouter

from backend.app.api.v1.daily_practice import router as daily_practice_router
from backend.app.api.v1.roleplay import router as roleplay_router


api_router = APIRouter()
api_router.include_router(daily_practice_router)
api_router.include_router(roleplay_router)
