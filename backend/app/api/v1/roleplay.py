from fastapi import APIRouter, HTTPException

from backend.app.schemas.roleplay import RoleplayIngameResponse
from backend.app.services.sample_roleplaying_adapter import (
    SampleRoleplayingAdapterError,
    get_sample_convenience_store_ingame,
)


router = APIRouter(prefix="/roleplay", tags=["roleplay"])


@router.get("/convenience-store/ingame", response_model=RoleplayIngameResponse)
async def convenience_store_ingame() -> RoleplayIngameResponse:
    try:
        return get_sample_convenience_store_ingame()
    except SampleRoleplayingAdapterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

