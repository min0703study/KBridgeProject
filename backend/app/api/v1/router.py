from fastapi import APIRouter

from backend.app.api.v1.roleplay import router as roleplay_router
from backend.app.api.v1.roleplay_sessions import router as roleplay_sessions_router


api_router = APIRouter()
api_router.include_router(roleplay_router)
api_router.include_router(roleplay_sessions_router)
