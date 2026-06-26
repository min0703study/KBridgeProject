from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.app.db.models import (
    RoleplayCharacter,
    RoleplayLocation,
    ScenarioLocation,
    ScenarioRoleplayCharacter,
    ScenarioVersion,
    Step,
    StepSampleAnswer,
)
from backend.app.schemas.roleplay import (
    CurrentRoleplayStep,
    RoleplayCharacterSummary,
    RoleplayIngameResponse,
    RoleplayIngameUiState,
    RoleplayLocationSummary,
    RoleplayScenarioSummary,
    RoleplayVersionSummary,
    StepSampleAnswerSummary,
)


class RoleplayIngameNotFoundError(ValueError):
    pass


async def get_convenience_store_ingame(session: AsyncSession) -> RoleplayIngameResponse:
    version = await get_default_scenario_version(session)
    step = await get_first_step(session, version.scenario_version_id)
    scenario_location = await _get_step_or_primary_scenario_location(
        session,
        version.scenario_version_id,
        step.primary_scenario_location_id,
    )
    scenario_character = await _get_step_or_primary_scenario_character(
        session,
        version.scenario_version_id,
        step.primary_scenario_roleplay_character_id,
    )
    total_steps = await _get_total_steps(session, version.scenario_version_id)
    sample_answers = await _get_step_sample_answers(session, step.step_id)

    location = scenario_location.roleplay_location
    character = scenario_character.roleplay_character

    return RoleplayIngameResponse(
        scenario=RoleplayScenarioSummary(
            scenario_id=str(version.scenario.scenario_id),
            title=version.scenario.title,
            description=version.scenario.description,
            difficulty=version.scenario.difficulty,
        ),
        version=RoleplayVersionSummary(
            scenario_version_id=str(version.scenario_version_id),
            learning_language=version.learning_language,
            default_system_language=version.default_system_language,
            default_total_chances=version.default_total_chances,
        ),
        location=RoleplayLocationSummary(
            scenario_location_id=str(scenario_location.scenario_location_id),
            roleplay_location_id=str(location.roleplay_location_id),
            name=location.name,
            description=location.description,
            background_image_url=location.background_image.public_url
            if location.background_image
            else None,
        ),
        character=RoleplayCharacterSummary(
            scenario_roleplay_character_id=str(scenario_character.scenario_roleplay_character_id),
            roleplay_character_id=str(character.roleplay_character_id),
            role_name=scenario_character.scenario_role_name,
            name=character.name,
            description=character.description,
            image_url=character.image_base.public_url if character.image_base else None,
        ),
        current_step=CurrentRoleplayStep(
            step_id=str(step.step_id),
            step_order=step.step_order,
            step_title=step.step_title,
            step_goal=step.step_goal,
            guidance_text=step.roleplay_guidance_text,
            scene_text=step.initial_scene_text,
            character_action_text=step.initial_roleplay_character_action_text,
            character_dialogue_text=step.initial_roleplay_character_dialogue_text,
            character_dialogue_language=step.initial_roleplay_character_dialogue_language,
            character_dialogue_translation_json=step.initial_roleplay_character_dialogue_translation_json,
            sample_answers=[
                StepSampleAnswerSummary(
                    step_sample_answer_id=str(answer.step_sample_answer_id),
                    text=answer.sample_answer_text,
                    language_code=answer.language_code,
                    display_order=answer.display_order,
                )
                for answer in sample_answers
            ],
        ),
        ui_state=RoleplayIngameUiState(
            total_chances=version.default_total_chances,
            remaining_chances=version.default_total_chances,
            current_step_order=step.step_order,
            total_steps=total_steps,
        ),
    )


async def get_default_scenario_version(session: AsyncSession) -> ScenarioVersion:
    result = await session.execute(
        select(ScenarioVersion)
        .options(joinedload(ScenarioVersion.scenario))
        .where(ScenarioVersion.status != "archived")
        .order_by(
            (ScenarioVersion.status == "published").desc(),
            ScenarioVersion.published_at.desc().nullslast(),
            ScenarioVersion.created_at.desc(),
        )
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise RoleplayIngameNotFoundError("No roleplay scenario version was found.")
    return version


async def _get_step_or_primary_scenario_location(
    session: AsyncSession,
    scenario_version_id: UUID,
    primary_scenario_location_id: UUID | None,
) -> ScenarioLocation:
    query = (
        select(ScenarioLocation)
        .options(
            joinedload(ScenarioLocation.roleplay_location).joinedload(
                RoleplayLocation.background_image
            )
        )
        .where(ScenarioLocation.scenario_version_id == scenario_version_id)
    )
    if primary_scenario_location_id:
        query = query.where(
            ScenarioLocation.scenario_location_id == primary_scenario_location_id
        )
    else:
        query = query.order_by(
            ScenarioLocation.is_primary.desc(),
            ScenarioLocation.display_order.asc(),
        )

    result = await session.execute(
        query.limit(1)
    )
    scenario_location = result.scalar_one_or_none()
    if scenario_location is None:
        raise RoleplayIngameNotFoundError("Roleplay scenario location was not found.")
    return scenario_location


async def _get_step_or_primary_scenario_character(
    session: AsyncSession,
    scenario_version_id: UUID,
    primary_scenario_roleplay_character_id: UUID | None,
) -> ScenarioRoleplayCharacter:
    query = (
        select(ScenarioRoleplayCharacter)
        .options(
            joinedload(ScenarioRoleplayCharacter.roleplay_character).joinedload(
                RoleplayCharacter.image_base
            )
        )
        .where(ScenarioRoleplayCharacter.scenario_version_id == scenario_version_id)
    )
    if primary_scenario_roleplay_character_id:
        query = query.where(
            ScenarioRoleplayCharacter.scenario_roleplay_character_id
            == primary_scenario_roleplay_character_id
        )
    else:
        query = query.order_by(
            ScenarioRoleplayCharacter.is_primary.desc(),
            ScenarioRoleplayCharacter.display_order.asc(),
        )

    result = await session.execute(
        query.limit(1)
    )
    scenario_character = result.scalar_one_or_none()
    if scenario_character is None:
        raise RoleplayIngameNotFoundError("Roleplay character was not found.")
    return scenario_character


async def get_first_step(session: AsyncSession, scenario_version_id: UUID) -> Step:
    result = await session.execute(
        select(Step)
        .where(Step.scenario_version_id == scenario_version_id)
        .order_by(Step.step_order.asc())
        .limit(1)
    )
    step = result.scalar_one_or_none()
    if step is None:
        raise RoleplayIngameNotFoundError("Roleplay first step was not found.")
    return step


async def _get_total_steps(session: AsyncSession, scenario_version_id: UUID) -> int:
    result = await session.execute(
        select(func.count(Step.step_id)).where(Step.scenario_version_id == scenario_version_id)
    )
    return int(result.scalar_one() or 1)


async def _get_step_sample_answers(
    session: AsyncSession, step_id: UUID
) -> list[StepSampleAnswer]:
    result = await session.execute(
        select(StepSampleAnswer)
        .where(StepSampleAnswer.step_id == step_id)
        .order_by(StepSampleAnswer.display_order.asc())
    )
    return list(result.scalars().all())
