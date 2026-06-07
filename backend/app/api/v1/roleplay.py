from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.roleplay import RoleplayIngameResponse, RoleplayTurnResponse
from backend.app.services.roleplay_ingame_service import (
    RoleplayIngameNotFoundError,
    get_convenience_store_ingame,
)


router = APIRouter(prefix="/roleplay", tags=["roleplay"])


@router.get("/convenience-store/ingame", response_model=RoleplayIngameResponse)
async def convenience_store_ingame(
    session: AsyncSession = Depends(get_db_session),
) -> RoleplayIngameResponse:
    try:
        return await get_convenience_store_ingame(session)
    except RoleplayIngameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/convenience-store/turn", response_model=RoleplayTurnResponse)
async def convenience_store_turn(
    audio_file: UploadFile = File(...),
    scenario_id: str | None = Form(default=None),
    step_id: str | None = Form(default=None),
    client_turn_id: str | None = Form(default=None),
) -> RoleplayTurnResponse:
    del audio_file, scenario_id, step_id, client_turn_id
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Use POST /api/v1/roleplay-sessions/{roleplay_session_id}/turns.",
    )
