from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.roleplay import RoleplayIngameResponse, RoleplayTurnResponse
from backend.app.services.roleplay_ingame_service import (
    RoleplayIngameNotFoundError,
    get_convenience_store_ingame,
)
from backend.app.services.roleplay_voice_service import (
    EmptyTranscriptError,
    InvalidAudioError,
    MissingProviderKeyError,
    run_convenience_store_turn,
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
    audio_bytes = await audio_file.read()

    try:
        return await run_convenience_store_turn(
            audio_bytes=audio_bytes,
            filename=audio_file.filename,
            scenario_id=scenario_id,
            step_id=step_id,
            client_turn_id=client_turn_id,
        )
    except InvalidAudioError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmptyTranscriptError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MissingProviderKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
