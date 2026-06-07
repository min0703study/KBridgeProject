from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import RoleplaySession, ScenarioVersion, Step, User
from backend.app.schemas.roleplay import (
    RoleplaySessionCreateRequest,
    RoleplaySessionCreateResponse,
)
from backend.app.services.roleplay_ingame_service import SCENARIO_VERSION_ID


class RoleplaySessionCreateError(ValueError):
    status_code = 400


class RoleplaySessionNotFoundError(RoleplaySessionCreateError):
    status_code = 404


async def create_roleplay_session(
    session: AsyncSession,
    payload: RoleplaySessionCreateRequest,
) -> RoleplaySessionCreateResponse:
    learner_id = _parse_uuid(payload.learner_id, "learner_id")
    scenario_version_id = (
        _parse_uuid(payload.scenario_version_id, "scenario_version_id")
        if payload.scenario_version_id
        else SCENARIO_VERSION_ID
    )

    learner = await _get_active_learner(session, learner_id)
    scenario_version = await _get_scenario_version(session, scenario_version_id)
    first_step = await _get_first_step(session, scenario_version_id)

    now = datetime.now(UTC)
    roleplay_session = RoleplaySession(
        roleplay_session_id=uuid4(),
        learner_id=learner.user_id,
        scenario_version_id=scenario_version.scenario_version_id,
        current_step_id=first_step.step_id,
        total_chances=scenario_version.default_total_chances,
        remaining_chances=scenario_version.default_total_chances,
        end_status="in_progress",
        started_at=now,
        ended_at=None,
        created_at=now,
        updated_at=now,
        current_step_fail_count=0,
    )

    session.add(roleplay_session)
    await session.commit()
    await session.refresh(roleplay_session)

    return RoleplaySessionCreateResponse(
        roleplay_session_id=str(roleplay_session.roleplay_session_id),
        learner_id=str(roleplay_session.learner_id),
        scenario_version_id=str(roleplay_session.scenario_version_id),
        current_step_id=str(roleplay_session.current_step_id),
        total_chances=roleplay_session.total_chances,
        remaining_chances=roleplay_session.remaining_chances,
        end_status=roleplay_session.end_status,
        current_step_fail_count=roleplay_session.current_step_fail_count,
    )


def _parse_uuid(value: str | None, field_name: str) -> UUID:
    if not value:
        raise RoleplaySessionCreateError(f"{field_name} is required.")

    try:
        return UUID(value)
    except ValueError as exc:
        raise RoleplaySessionCreateError(f"{field_name} must be a valid UUID.") from exc


async def _get_active_learner(session: AsyncSession, learner_id: UUID) -> User:
    result = await session.execute(
        select(User).where(User.user_id == learner_id, User.status == "active")
    )
    learner = result.scalar_one_or_none()
    if learner is None:
        raise RoleplaySessionNotFoundError("Active learner was not found.")
    return learner


async def _get_scenario_version(
    session: AsyncSession, scenario_version_id: UUID
) -> ScenarioVersion:
    result = await session.execute(
        select(ScenarioVersion).where(
            ScenarioVersion.scenario_version_id == scenario_version_id
        )
    )
    scenario_version = result.scalar_one_or_none()
    if scenario_version is None:
        raise RoleplaySessionNotFoundError("Scenario version was not found.")
    return scenario_version


async def _get_first_step(session: AsyncSession, scenario_version_id: UUID) -> Step:
    result = await session.execute(
        select(Step)
        .where(Step.scenario_version_id == scenario_version_id)
        .order_by(Step.step_order.asc())
        .limit(1)
    )
    first_step = result.scalar_one_or_none()
    if first_step is None:
        raise RoleplaySessionNotFoundError("First step was not found.")
    return first_step
