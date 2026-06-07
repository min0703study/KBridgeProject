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


LOCATION_ID = UUID("11111111-1111-4111-8111-111111111111")
CHARACTER_ID = UUID("22222222-2222-4222-8222-222222222222")
SCENARIO_ID = UUID("33333333-3333-4333-8333-333333333333")
SCENARIO_VERSION_ID = UUID("44444444-4444-4444-8444-444444444444")
SCENARIO_LOCATION_ID = UUID("55555555-5555-4555-8555-555555555555")
SCENARIO_ROLEPLAY_CHARACTER_ID = UUID("66666666-6666-4666-8666-666666666666")


class RoleplayIngameNotFoundError(ValueError):
    pass


async def get_convenience_store_ingame(session: AsyncSession) -> RoleplayIngameResponse:
    version = await _get_required_version(session)
    scenario_location = await _get_required_scenario_location(session)
    scenario_character = await _get_required_scenario_character(session)
    step = await _get_required_first_step(session)
    total_steps = await _get_total_steps(session)
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


async def _get_required_version(session: AsyncSession) -> ScenarioVersion:
    result = await session.execute(
        select(ScenarioVersion)
        .options(joinedload(ScenarioVersion.scenario))
        .where(
            ScenarioVersion.scenario_version_id == SCENARIO_VERSION_ID,
            ScenarioVersion.scenario_id == SCENARIO_ID,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise RoleplayIngameNotFoundError("Convenience Store scenario version was not found.")
    return version


async def _get_required_scenario_location(session: AsyncSession) -> ScenarioLocation:
    result = await session.execute(
        select(ScenarioLocation)
        .options(
            joinedload(ScenarioLocation.roleplay_location).joinedload(
                RoleplayLocation.background_image
            )
        )
        .where(
            ScenarioLocation.scenario_location_id == SCENARIO_LOCATION_ID,
            ScenarioLocation.scenario_version_id == SCENARIO_VERSION_ID,
            ScenarioLocation.roleplay_location_id == LOCATION_ID,
        )
    )
    scenario_location = result.scalar_one_or_none()
    if scenario_location is None:
        raise RoleplayIngameNotFoundError("Convenience Store scenario location was not found.")
    return scenario_location


async def _get_required_scenario_character(session: AsyncSession) -> ScenarioRoleplayCharacter:
    result = await session.execute(
        select(ScenarioRoleplayCharacter)
        .options(
            joinedload(ScenarioRoleplayCharacter.roleplay_character).joinedload(
                RoleplayCharacter.image_base
            )
        )
        .where(
            ScenarioRoleplayCharacter.scenario_roleplay_character_id
            == SCENARIO_ROLEPLAY_CHARACTER_ID,
            ScenarioRoleplayCharacter.scenario_version_id == SCENARIO_VERSION_ID,
            ScenarioRoleplayCharacter.roleplay_character_id == CHARACTER_ID,
        )
    )
    scenario_character = result.scalar_one_or_none()
    if scenario_character is None:
        raise RoleplayIngameNotFoundError("Convenience Store roleplay character was not found.")
    return scenario_character


async def _get_required_first_step(session: AsyncSession) -> Step:
    result = await session.execute(
        select(Step)
        .where(
            Step.scenario_version_id == SCENARIO_VERSION_ID,
            Step.primary_scenario_location_id == SCENARIO_LOCATION_ID,
            Step.primary_scenario_roleplay_character_id == SCENARIO_ROLEPLAY_CHARACTER_ID,
        )
        .order_by(Step.step_order.asc())
        .limit(1)
    )
    step = result.scalar_one_or_none()
    if step is None:
        raise RoleplayIngameNotFoundError("Convenience Store first step was not found.")
    return step


async def _get_total_steps(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(Step.step_id)).where(Step.scenario_version_id == SCENARIO_VERSION_ID)
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
