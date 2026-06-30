from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.daily_practice import (
    AttemptCreateRequest,
    AttemptResponse,
    AttemptSubmitRequest,
    AttemptSubmitResponse,
    DailyPracticeActivityResponse,
    LearnerCreateRequest,
    LearnerResponse,
)
from backend.app.services.daily_practice_service import (
    DailyPracticeConflictError,
    DailyPracticeNotFoundError,
    create_attempt,
    create_or_get_learner,
    get_activity_by_code,
    submit_attempt,
)


router = APIRouter(prefix="/daily-practice", tags=["daily-practice"])


@router.post("/learners", response_model=LearnerResponse)
async def create_learner(
    payload: LearnerCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LearnerResponse:
    try:
        learner = await create_or_get_learner(
            session,
            name=payload.name,
            email=str(payload.email),
            default_system_language=payload.default_system_language,
            learning_language=payload.learning_language,
        )
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LearnerResponse(**learner)


@router.get("/activities/{activity_code}", response_model=DailyPracticeActivityResponse)
async def read_activity(
    activity_code: str,
    session: AsyncSession = Depends(get_db_session),
) -> DailyPracticeActivityResponse:
    try:
        activity = await get_activity_by_code(session, activity_code)
    except DailyPracticeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DailyPracticeActivityResponse(**activity)


@router.post("/attempts", response_model=AttemptResponse)
async def start_attempt(
    payload: AttemptCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AttemptResponse:
    try:
        attempt = await create_attempt(
            session,
            learner_id=payload.learner_id,
            activity_code=payload.activity_code,
        )
    except DailyPracticeNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AttemptResponse(**attempt)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptSubmitResponse)
async def submit_daily_practice_attempt(
    attempt_id: UUID,
    payload: AttemptSubmitRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AttemptSubmitResponse:
    try:
        result = await submit_attempt(
            session,
            attempt_id=attempt_id,
            answers=[answer.model_dump() for answer in payload.answers],
        )
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DailyPracticeNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DailyPracticeConflictError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AttemptSubmitResponse(**result)
