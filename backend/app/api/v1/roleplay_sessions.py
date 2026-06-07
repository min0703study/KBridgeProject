from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.roleplay import (
    RoleplaySessionCreateRequest,
    RoleplaySessionCreateResponse,
)
from backend.app.services.roleplay_session_service import (
    RoleplaySessionCreateError,
    create_roleplay_session,
)
from backend.app.schemas.roleplay import RoleplayTurnResponse
from backend.app.services.roleplay_session_turn_service import (
    ContextBuilderError,
    EmptyTranscriptError,
    GameRuleEngineError,
    InvalidAudioError,
    JudgeNodeError,
    MissingProviderKeyError,
    RoleplaySessionTurnError,
    run_roleplay_session_turn,
)


router = APIRouter(prefix="/roleplay-sessions", tags=["roleplay-sessions"])


@router.post(
    "",
    response_model=RoleplaySessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    payload: RoleplaySessionCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RoleplaySessionCreateResponse:
    try:
        return await create_roleplay_session(session, payload)
    except RoleplaySessionCreateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{roleplay_session_id}/turns", response_model=RoleplayTurnResponse)
async def create_session_turn(
    roleplay_session_id: str,
    audio_file: UploadFile = File(...),
    client_turn_id: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> RoleplayTurnResponse:
    audio_bytes = await audio_file.read()

    try:
        return await run_roleplay_session_turn(
            session=session,
            roleplay_session_id=roleplay_session_id,
            audio_bytes=audio_bytes,
            filename=audio_file.filename,
            client_turn_id=client_turn_id,
        )
    except InvalidAudioError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmptyTranscriptError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (MissingProviderKeyError, TypeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (
        RoleplaySessionTurnError,
        ContextBuilderError,
        JudgeNodeError,
        GameRuleEngineError,
    ) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
