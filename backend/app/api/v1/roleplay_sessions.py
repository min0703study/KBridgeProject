from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from backend.app.schemas.roleplay import (
    RoleplayDevPerfectAnswerRequest,
    RoleplaySessionCreateRequest,
    RoleplaySessionCreateResponse,
    RoleplaySessionStatus,
    RoleplayTextTurnRequest,
)
from backend.app.schemas.roleplay import RoleplayTurnResponse
from backend.app.services.sample_roleplaying_adapter import (
    SampleRoleplayingAdapterError,
    abandon_sample_roleplay_session,
    create_sample_roleplay_session,
    run_sample_roleplay_session_dev_perfect_answer_turn,
    run_sample_roleplay_session_text_turn,
    run_sample_roleplay_session_turn,
)


router = APIRouter(prefix="/roleplay-sessions", tags=["roleplay-sessions"])


@router.post(
    "",
    response_model=RoleplaySessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    payload: RoleplaySessionCreateRequest,
) -> RoleplaySessionCreateResponse:
    try:
        return create_sample_roleplay_session(payload)
    except SampleRoleplayingAdapterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{roleplay_session_id}/turns", response_model=RoleplayTurnResponse)
async def create_session_turn(
    roleplay_session_id: str,
    audio_file: UploadFile = File(...),
    client_turn_id: str | None = Form(default=None),
) -> RoleplayTurnResponse:
    audio_bytes = await audio_file.read()

    try:
        return await run_sample_roleplay_session_turn(
            roleplay_session_id=roleplay_session_id,
            audio_bytes=audio_bytes,
            filename=audio_file.filename,
            client_turn_id=client_turn_id,
        )
    except SampleRoleplayingAdapterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{roleplay_session_id}/turns/text", response_model=RoleplayTurnResponse)
async def create_session_text_turn(
    roleplay_session_id: str,
    payload: RoleplayTextTurnRequest,
) -> RoleplayTurnResponse:
    try:
        return await run_sample_roleplay_session_text_turn(roleplay_session_id, payload)
    except SampleRoleplayingAdapterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{roleplay_session_id}/turns/dev-perfect-answer", response_model=RoleplayTurnResponse)
async def create_session_dev_perfect_answer_turn(
    roleplay_session_id: str,
    payload: RoleplayDevPerfectAnswerRequest | None = None,
) -> RoleplayTurnResponse:
    try:
        return await run_sample_roleplay_session_dev_perfect_answer_turn(
            roleplay_session_id, payload
        )
    except SampleRoleplayingAdapterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.patch("/{roleplay_session_id}/abandon", response_model=RoleplaySessionStatus)
async def abandon_session(roleplay_session_id: str) -> RoleplaySessionStatus:
    """학생이 세션을 중도 포기(뒤로가기/종료 버튼)했을 때 호출. 멱등 — 이미 terminal이면 그대로 반환."""
    try:
        return abandon_sample_roleplay_session(roleplay_session_id)
    except SampleRoleplayingAdapterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
