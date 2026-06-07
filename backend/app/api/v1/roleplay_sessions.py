from fastapi import APIRouter, Depends, HTTPException, status
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
