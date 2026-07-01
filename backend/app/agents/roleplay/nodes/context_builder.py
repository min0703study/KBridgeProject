from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.app.agents.roleplay.logging import log_node_completed
from backend.app.agents.roleplay.state import AgentState
from backend.app.db.models import (
    Message,
    RoleplayCharacter,
    RoleplayLocation,
    RoleplaySession,
    ScenarioLocation,
    ScenarioRoleplayCharacter,
    ScenarioVersion,
    Step,
    StepSampleAnswer,
)


class ContextBuilderError(ValueError):
    status_code = 400


class ContextNotFoundError(ContextBuilderError):
    status_code = 404


class ContextForbiddenError(ContextBuilderError):
    status_code = 403


class ContextConflictError(ContextBuilderError):
    status_code = 409


def make_context_builder_node(session: AsyncSession):
    async def context_builder_node(state: AgentState) -> AgentState:
        roleplay_session_id = _parse_uuid(state["roleplay_session_id"], "roleplay_session_id")
        learner_id = _parse_uuid(state["learner_id"], "learner_id")

        roleplay_session = await _load_session(session, roleplay_session_id)
        if roleplay_session.learner_id != learner_id:
            raise ContextForbiddenError("Learner does not own this roleplay session.")
        if roleplay_session.end_status != "in_progress":
            raise ContextConflictError("Roleplay session is not in progress.")
        if roleplay_session.current_step_id is None:
            raise ContextConflictError("Roleplay session has no current step.")

        current_step = await _load_step(session, roleplay_session.current_step_id)
        scenario_version = await _load_scenario_version(
            session,
            roleplay_session.scenario_version_id,
        )
        scenario_character = await _load_step_or_primary_character(
            session,
            scenario_version.scenario_version_id,
            current_step.primary_scenario_roleplay_character_id,
        )
        scenario_location = await _load_step_or_primary_location(
            session,
            scenario_version.scenario_version_id,
            current_step.primary_scenario_location_id,
        )
        recent_messages = await _load_recent_messages(session, roleplay_session_id, limit=8)
        sample_answers = await _load_step_sample_answers(
            session,
            current_step.step_id,
            scenario_version.learning_language,
        )

        state["session"] = _serialize_session(roleplay_session)
        state["scenario_version"] = _serialize_scenario_version(scenario_version)
        state["scenario"] = {
            "scenario_id": str(scenario_version.scenario.scenario_id),
            "title": scenario_version.scenario.title,
            "description": scenario_version.scenario.description,
            "difficulty": scenario_version.scenario.difficulty,
        }
        state["current_step"] = _serialize_step(current_step)
        state["character"] = _serialize_character(scenario_character)
        state["location"] = _serialize_location(scenario_location)
        state["recent_messages"] = [_serialize_message(message) for message in recent_messages]
        state["step_sample_answers"] = [
            answer.sample_answer_text for answer in sample_answers
        ]
        state["last_character_message_text"] = _extract_last_message(
            state["recent_messages"],
            sender_type="roleplay_character",
        )
        state["last_learner_message_text"] = _extract_last_message(
            state["recent_messages"],
            sender_type="learner",
        )

        log_node_completed(
            "context_builder",
            {
                "session": state["session"],
                "scenario_version": state["scenario_version"],
                "scenario": state["scenario"],
                "current_step": state["current_step"],
                "character": state["character"],
                "location": state["location"],
                "recent_messages": state["recent_messages"],
                "step_sample_answers": state["step_sample_answers"],
                "last_character_message_text": state["last_character_message_text"],
                "last_learner_message_text": state["last_learner_message_text"],
            },
        )
        return state

    return context_builder_node


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ContextBuilderError(f"{field_name} must be a valid UUID.") from exc


async def _load_session(
    session: AsyncSession,
    roleplay_session_id: UUID,
) -> RoleplaySession:
    result = await session.execute(
        select(RoleplaySession).where(
            RoleplaySession.roleplay_session_id == roleplay_session_id
        )
    )
    roleplay_session = result.scalar_one_or_none()
    if roleplay_session is None:
        raise ContextNotFoundError("Roleplay session was not found.")
    return roleplay_session


async def _load_step(session: AsyncSession, step_id: UUID) -> Step:
    result = await session.execute(select(Step).where(Step.step_id == step_id))
    step = result.scalar_one_or_none()
    if step is None:
        raise ContextNotFoundError("Current step was not found.")
    return step


async def _load_scenario_version(
    session: AsyncSession,
    scenario_version_id: UUID,
) -> ScenarioVersion:
    result = await session.execute(
        select(ScenarioVersion)
        .options(joinedload(ScenarioVersion.scenario))
        .where(ScenarioVersion.scenario_version_id == scenario_version_id)
    )
    scenario_version = result.scalar_one_or_none()
    if scenario_version is None:
        raise ContextNotFoundError("Scenario version was not found.")
    return scenario_version


async def _load_step_or_primary_character(
    session: AsyncSession,
    scenario_version_id: UUID,
    primary_scenario_roleplay_character_id: UUID | None,
) -> ScenarioRoleplayCharacter:
    query = (
        select(ScenarioRoleplayCharacter)
        .options(joinedload(ScenarioRoleplayCharacter.roleplay_character))
        .where(ScenarioRoleplayCharacter.scenario_version_id == scenario_version_id)
    )

    if primary_scenario_roleplay_character_id:
        query = query.where(
            ScenarioRoleplayCharacter.scenario_roleplay_character_id
            == primary_scenario_roleplay_character_id
        )
    else:
        query = query.where(ScenarioRoleplayCharacter.is_primary.is_(True)).order_by(
            ScenarioRoleplayCharacter.display_order.asc()
        )

    result = await session.execute(query.limit(1))
    scenario_character = result.scalar_one_or_none()
    if scenario_character is None:
        raise ContextNotFoundError("Roleplay character was not found.")
    return scenario_character


async def _load_step_or_primary_location(
    session: AsyncSession,
    scenario_version_id: UUID,
    primary_scenario_location_id: UUID | None,
) -> ScenarioLocation:
    query = (
        select(ScenarioLocation)
        .options(joinedload(ScenarioLocation.roleplay_location))
        .where(ScenarioLocation.scenario_version_id == scenario_version_id)
    )

    if primary_scenario_location_id:
        query = query.where(
            ScenarioLocation.scenario_location_id == primary_scenario_location_id
        )
    else:
        query = query.where(ScenarioLocation.is_primary.is_(True)).order_by(
            ScenarioLocation.display_order.asc()
        )

    result = await session.execute(query.limit(1))
    scenario_location = result.scalar_one_or_none()
    if scenario_location is None:
        raise ContextNotFoundError("Roleplay location was not found.")
    return scenario_location


async def _load_recent_messages(
    session: AsyncSession,
    roleplay_session_id: UUID,
    limit: int,
) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.roleplay_session_id == roleplay_session_id)
        .order_by(Message.message_order.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def _load_step_sample_answers(
    session: AsyncSession,
    step_id: UUID,
    language_code: str,
) -> list[StepSampleAnswer]:
    result = await session.execute(
        select(StepSampleAnswer)
        .where(
            StepSampleAnswer.step_id == step_id,
            StepSampleAnswer.language_code == language_code,
        )
        .order_by(StepSampleAnswer.display_order.asc())
    )
    return list(result.scalars().all())


def _serialize_session(roleplay_session: RoleplaySession) -> dict:
    return {
        "roleplay_session_id": str(roleplay_session.roleplay_session_id),
        "learner_id": str(roleplay_session.learner_id),
        "scenario_version_id": str(roleplay_session.scenario_version_id),
        "current_step_id": str(roleplay_session.current_step_id)
        if roleplay_session.current_step_id
        else None,
        "total_chances": roleplay_session.total_chances,
        "remaining_chances": roleplay_session.remaining_chances,
        "end_status": roleplay_session.end_status,
        "current_step_fail_count": roleplay_session.current_step_fail_count,
    }


def _serialize_scenario_version(scenario_version: ScenarioVersion) -> dict:
    return {
        "scenario_version_id": str(scenario_version.scenario_version_id),
        "scenario_id": str(scenario_version.scenario_id),
        "version_number": scenario_version.version_number,
        "learning_language": scenario_version.learning_language,
        "default_system_language": scenario_version.default_system_language,
        "default_total_chances": scenario_version.default_total_chances,
        "status": scenario_version.status,
    }


def _serialize_step(step: Step) -> dict:
    return {
        "step_id": str(step.step_id),
        "scenario_version_id": str(step.scenario_version_id),
        "step_order": step.step_order,
        "step_title": step.step_title,
        "step_goal": step.step_goal,
        "initial_scene_text": step.initial_scene_text,
        "initial_roleplay_character_action_text": step.initial_roleplay_character_action_text,
        "initial_roleplay_character_dialogue_text": step.initial_roleplay_character_dialogue_text,
        "initial_roleplay_character_dialogue_language": step.initial_roleplay_character_dialogue_language,
        "initial_roleplay_character_dialogue_translation_json": step.initial_roleplay_character_dialogue_translation_json,
        "roleplay_guidance_text": step.roleplay_guidance_text,
        "primary_scenario_roleplay_character_id": str(step.primary_scenario_roleplay_character_id)
        if step.primary_scenario_roleplay_character_id
        else None,
        "primary_scenario_location_id": str(step.primary_scenario_location_id)
        if step.primary_scenario_location_id
        else None,
    }


def _serialize_character(scenario_character: ScenarioRoleplayCharacter) -> dict:
    character: RoleplayCharacter = scenario_character.roleplay_character
    return {
        "scenario_roleplay_character_id": str(
            scenario_character.scenario_roleplay_character_id
        ),
        "roleplay_character_id": str(character.roleplay_character_id),
        "role_name": scenario_character.scenario_role_name,
        "name": character.name,
        "description": character.description,
        "persona_prompt": character.persona_prompt,
    }


def _serialize_location(scenario_location: ScenarioLocation) -> dict:
    location: RoleplayLocation = scenario_location.roleplay_location
    return {
        "scenario_location_id": str(scenario_location.scenario_location_id),
        "roleplay_location_id": str(location.roleplay_location_id),
        "name": location.name,
        "description": location.description,
        "location_prompt": location.location_prompt,
    }


def _serialize_message(message: Message) -> dict:
    return {
        "message_id": str(message.message_id),
        "roleplay_session_id": str(message.roleplay_session_id),
        "roleplay_turn_id": str(message.roleplay_turn_id)
        if message.roleplay_turn_id
        else None,
        "step_id": str(message.step_id) if message.step_id else None,
        "scenario_roleplay_character_id": str(message.scenario_roleplay_character_id)
        if message.scenario_roleplay_character_id
        else None,
        "message_order": message.message_order,
        "sender_type": message.sender_type,
        "generated_by": message.generated_by,
        "message_type": message.message_type,
        "text_content": message.text_content,
        "text_language": message.text_language,
        "translation_json": message.translation_json,
        "hint_level": message.hint_level,
    }


def _extract_last_message(
    messages: list[dict],
    *,
    sender_type: str,
) -> str | None:
    for message in reversed(messages):
        if message.get("sender_type") == sender_type:
            return message.get("text_content")
    return None
