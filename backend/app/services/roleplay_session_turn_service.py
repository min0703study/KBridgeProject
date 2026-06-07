from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.roleplay.graph import build_roleplay_turn_graph
from backend.app.agents.roleplay.logging import log_node_completed
from backend.app.agents.roleplay.nodes.context_builder import (
    ContextBuilderError,
    make_context_builder_node,
)
from backend.app.agents.roleplay.nodes.domain_persistence import (
    DomainPersistenceError,
    make_domain_persistence_node,
)
from backend.app.agents.roleplay.nodes.game_rule_engine import (
    GameRuleEngineError,
    make_game_rule_engine_node,
)
from backend.app.agents.roleplay.nodes.judge import JudgeNodeError
from backend.app.agents.roleplay.nodes.response_pack import ResponsePackNodeError
from backend.app.agents.roleplay.schemas import (
    CorrectionItem,
    JudgeResult,
    ResponseMessageDraft,
    ResponsePack,
)
from backend.app.agents.roleplay.state import build_initial_state
from backend.app.db.models import RoleplaySession, Step
from backend.app.schemas.roleplay import (
    AssistantMessage,
    CorrectionFeedback,
    Evaluation,
    RoleplaySessionStatus,
    RoleplayTurnMessage,
    RoleplayTurnResponse,
    RoleplayUiState,
)
from backend.app.services.roleplay_voice_service import (
    EmptyTranscriptError,
    InvalidAudioError,
    MissingProviderKeyError,
    text_to_speech_base64,
    transcribe_wav_audio,
)


class RoleplaySessionTurnError(ValueError):
    status_code = 400


class RoleplaySessionTurnNotFoundError(RoleplaySessionTurnError):
    status_code = 404


async def run_roleplay_session_turn(
    *,
    session: AsyncSession,
    roleplay_session_id: str,
    audio_bytes: bytes,
    filename: str | None,
    client_turn_id: str | None,
) -> RoleplayTurnResponse:
    del filename, client_turn_id

    parsed_session_id = _parse_uuid(roleplay_session_id, "roleplay_session_id")
    learner_id = await _get_session_learner_id(session, parsed_session_id)

    transcript = transcribe_wav_audio(audio_bytes)
    return await _run_roleplay_turn_with_transcript(
        session=session,
        roleplay_session_id=parsed_session_id,
        learner_id=learner_id,
        transcript=transcript,
        input_method="voice",
    )


async def run_roleplay_session_text_turn(
    *,
    session: AsyncSession,
    roleplay_session_id: str,
    text_content: str,
    client_turn_id: str | None,
) -> RoleplayTurnResponse:
    del client_turn_id

    transcript = text_content.strip()
    if not transcript:
        raise EmptyTranscriptError("Text input must not be empty.")

    parsed_session_id = _parse_uuid(roleplay_session_id, "roleplay_session_id")
    learner_id = await _get_session_learner_id(session, parsed_session_id)

    return await _run_roleplay_turn_with_transcript(
        session=session,
        roleplay_session_id=parsed_session_id,
        learner_id=learner_id,
        transcript=transcript,
        input_method="text",
    )


async def run_roleplay_session_dev_perfect_answer_turn(
    *,
    session: AsyncSession,
    roleplay_session_id: str,
    client_turn_id: str | None,
) -> RoleplayTurnResponse:
    del client_turn_id

    parsed_session_id = _parse_uuid(roleplay_session_id, "roleplay_session_id")
    learner_id = await _get_session_learner_id(session, parsed_session_id)

    state = build_initial_state(
        roleplay_session_id=str(parsed_session_id),
        learner_id=str(learner_id),
        learner_input_text="",
        input_method="text",
    )
    state = await make_context_builder_node(session)(state)
    state["learner_input_text"] = _dev_perfect_answer_text(state)
    state["judge_result"] = JudgeResult(
        evaluation_result="pass",
        confidence=1.0,
        inferred_intent_text="Developer perfect-answer bypass.",
        step_goal_matched=True,
        communication_success=True,
        issue_tags=[],
        correction_needed=False,
        cultural_issue_detected=False,
        evaluation_reason_text="Developer perfect-answer bypass marked this step as passed.",
    )
    state = await make_game_rule_engine_node(session)(state)
    state["next_step"] = await _load_display_next_step(session, state)
    state["response_pack"] = _build_dev_perfect_response_pack(state)
    state = await make_domain_persistence_node(session)(state)

    log_node_completed(
        "dev_perfect_answer",
        {
            "roleplay_session_id": str(parsed_session_id),
            "learner_input_text": state["learner_input_text"],
            "rule_decision": state["rule_decision"],
            "response_pack": state["response_pack"],
        },
    )

    return await _build_turn_response(
        session=session,
        final_state=state,
        transcript=state["learner_input_text"],
        include_tts=False,
    )


async def _run_roleplay_turn_with_transcript(
    *,
    session: AsyncSession,
    roleplay_session_id: UUID,
    learner_id: UUID,
    transcript: str,
    input_method: str,
) -> RoleplayTurnResponse:
    graph = build_roleplay_turn_graph(session)
    final_state = await graph.ainvoke(
        build_initial_state(
            roleplay_session_id=str(roleplay_session_id),
            learner_id=str(learner_id),
            learner_input_text=transcript,
            input_method=input_method,
        )
    )

    return await _build_turn_response(
        session=session,
        final_state=final_state,
        transcript=transcript,
        include_tts=True,
    )


async def _build_turn_response(
    *,
    session: AsyncSession,
    final_state: dict,
    transcript: str,
    include_tts: bool,
) -> RoleplayTurnResponse:
    response_pack: ResponsePack = final_state["response_pack"]
    assistant_ko = response_pack.character_dialogue_text or "네, 알겠습니다."
    audio_base64 = text_to_speech_base64(assistant_ko) if include_tts else ""
    correction_item = _first_correction_item(response_pack.correction_items)
    feedback = _build_feedback(correction_item) if correction_item else None
    judge_result = final_state["judge_result"]
    rule_decision = final_state["rule_decision"]
    current_step = final_state["current_step"]
    next_step = final_state.get("next_step")
    display_step = _display_step(current_step, next_step, rule_decision)
    total_steps = await _get_total_steps(session, current_step)
    persistence_result = final_state["persistence_result"]
    session_after = persistence_result.session_after if persistence_result else {}
    end_status = str(session_after.get("end_status") or "in_progress")

    public_issue_tags = [
        tag
        for tag in (judge_result.issue_tags if judge_result else [])
        if tag
        in {
            "grammar",
            "vocabulary",
            "politeness",
            "naturalness",
            "culturalContext",
            "taskExpression",
            "clarity",
            "offTopic",
        }
    ]

    return RoleplayTurnResponse(
        transcript=transcript,
        assistant_message=AssistantMessage(
            ko=assistant_ko,
            en=response_pack.character_dialogue_translation_text or "",
            audio_base64=audio_base64,
        ),
        evaluation=Evaluation(
            result=judge_result.evaluation_result if judge_result else "soft_pass",
            issue_tags=public_issue_tags,
            correction_needed=bool(judge_result and judge_result.correction_needed),
        ),
        feedback=feedback,
        ui_state=RoleplayUiState(
            remaining_chances=_remaining_chances(final_state, session_after),
            score_count=0,
            current_step_label=_current_step_label(display_step),
            current_step_order=int(display_step.get("step_order") or 1),
            current_step_guidance_text=display_step.get("roleplay_guidance_text"),
            total_steps=total_steps,
            should_show_feedback=feedback is not None,
        ),
        turn_messages=[
            RoleplayTurnMessage(
                message_id=message.message_id,
                sender_type=message.sender_type,
                message_type=message.message_type,
                text_content=message.text_content,
                text_language=message.text_language,
                translation_json=message.translation_json,
                step_id=message.step_id,
                hint_level=message.hint_level,
            )
            for message in (persistence_result.turn_messages if persistence_result else [])
        ],
        session_status=RoleplaySessionStatus(
            end_status=end_status,
            is_ended=end_status in {"completed", "failed", "abandoned"},
            current_step_id=session_after.get("current_step_id"),
            created_turn_id=persistence_result.created_turn_id
            if persistence_result
            else None,
        ),
    )


def _dev_perfect_answer_text(final_state: dict) -> str:
    sample_answers = final_state.get("step_sample_answers") or []
    if sample_answers:
        return str(sample_answers[0]).strip()

    current_step = final_state.get("current_step") or {}
    fallback = (
        current_step.get("roleplay_guidance_text")
        or current_step.get("step_goal")
        or "Okay."
    )
    return str(fallback).strip()


async def _load_display_next_step(session: AsyncSession, final_state: dict) -> dict | None:
    rule_decision = final_state["rule_decision"]
    if not rule_decision or not rule_decision.next_step_id:
        return None

    result = await session.execute(
        select(Step).where(Step.step_id == _parse_uuid(rule_decision.next_step_id, "next_step_id"))
    )
    step = result.scalar_one_or_none()
    if step is None:
        raise RoleplaySessionTurnNotFoundError("Next step was not found.")
    return _serialize_step_for_turn(step)


def _serialize_step_for_turn(step: Step) -> dict:
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


def _build_dev_perfect_response_pack(final_state: dict) -> ResponsePack:
    rule_decision = final_state["rule_decision"]
    current_step = final_state["current_step"]
    next_step = final_state.get("next_step")
    target_step = (
        next_step
        if rule_decision
        and rule_decision.progress_outcome == "advance_to_next_step"
        and next_step
        else current_step
    )
    drafts: list[ResponseMessageDraft] = []

    if target_step is next_step:
        scene_text = target_step.get("initial_scene_text")
        if scene_text:
            drafts.append(
                ResponseMessageDraft(
                    message_type="scene_text",
                    text_content=scene_text,
                    text_language=_system_language(final_state),
                    step_id=target_step.get("step_id"),
                )
            )

        action_text = target_step.get("initial_roleplay_character_action_text")
        if action_text:
            drafts.append(
                ResponseMessageDraft(
                    message_type="roleplay_character_action_text",
                    text_content=action_text,
                    text_language=_system_language(final_state),
                    step_id=target_step.get("step_id"),
                    scenario_roleplay_character_id=final_state["character"].get(
                        "scenario_roleplay_character_id"
                    ),
                )
            )

    dialogue_text = _dev_dialogue_text(final_state, target_step)
    drafts.append(
        ResponseMessageDraft(
            message_type="roleplay_character_dialogue_text",
            text_content=dialogue_text,
            text_language=target_step.get("initial_roleplay_character_dialogue_language")
            or _learning_language(final_state),
            translation_json=_dev_dialogue_translation_json(final_state, target_step),
            step_id=target_step.get("step_id"),
            scenario_roleplay_character_id=final_state["character"].get(
                "scenario_roleplay_character_id"
            ),
        )
    )
    return ResponsePack(message_drafts=drafts, correction_items=[])


def _dev_dialogue_text(final_state: dict, target_step: dict) -> str:
    authored_dialogue = target_step.get("initial_roleplay_character_dialogue_text")
    if authored_dialogue:
        return authored_dialogue

    rule_decision = final_state["rule_decision"]
    if rule_decision and rule_decision.progress_outcome == "complete_session":
        return _language_text(final_state, "좋습니다. 역할극을 마무리하겠습니다.", "Good job. The roleplay is complete.")
    return _language_text(final_state, "좋습니다. 계속해 보겠습니다.", "Good. Let's continue.")


def _dev_dialogue_translation_json(final_state: dict, target_step: dict) -> dict | None:
    translation_json = target_step.get("initial_roleplay_character_dialogue_translation_json")
    if isinstance(translation_json, dict):
        return translation_json

    rule_decision = final_state["rule_decision"]
    if rule_decision and rule_decision.progress_outcome == "complete_session":
        return {"en": "Good job. The roleplay is complete."}
    return {"en": "Good. Let's continue."}


def _learning_language(final_state: dict) -> str:
    return final_state["scenario_version"].get("learning_language") or "ko"


def _system_language(final_state: dict) -> str:
    return final_state["scenario_version"].get("default_system_language") or "en"


def _language_text(final_state: dict, ko_text: str, en_text: str) -> str:
    return ko_text if _learning_language(final_state) == "ko" else en_text


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise RoleplaySessionTurnError(f"{field_name} must be a valid UUID.") from exc


async def _get_session_learner_id(session: AsyncSession, roleplay_session_id: UUID) -> UUID:
    result = await session.execute(
        select(RoleplaySession.learner_id).where(
            RoleplaySession.roleplay_session_id == roleplay_session_id
        )
    )
    learner_id = result.scalar_one_or_none()
    if learner_id is None:
        raise RoleplaySessionTurnNotFoundError("Roleplay session was not found.")
    return learner_id


def _remaining_chances(final_state: dict, session_after: dict) -> int:
    if session_after.get("remaining_chances") is not None:
        return int(session_after["remaining_chances"])
    rule_decision = final_state["rule_decision"]
    if rule_decision:
        return rule_decision.remaining_chances_after
    return int(final_state["session"].get("remaining_chances") or 0)


def _display_step(
    current_step: dict,
    next_step: dict | None,
    rule_decision,
) -> dict:
    return (
        next_step
        if rule_decision
        and rule_decision.progress_outcome == "advance_to_next_step"
        and next_step
        else current_step
    )


def _current_step_label(display_step: dict) -> str:
    return f"Step {display_step.get('step_order')}: {display_step.get('step_title')}"


async def _get_total_steps(session: AsyncSession, current_step: dict) -> int:
    scenario_version_id = current_step.get("scenario_version_id")
    if not scenario_version_id:
        return 1

    result = await session.execute(
        select(func.count(Step.step_id)).where(
            Step.scenario_version_id
            == _parse_uuid(str(scenario_version_id), "scenario_version_id")
        )
    )
    return int(result.scalar_one() or 1)


def _first_correction_item(items: list[CorrectionItem]) -> CorrectionItem | None:
    return items[0] if items else None


def _build_feedback(correction_item: CorrectionItem) -> CorrectionFeedback:
    return CorrectionFeedback(
        previous_text=correction_item.original_text,
        better_way=correction_item.corrected_text,
        politeness_note=correction_item.reason_text,
        grammar_note="Use a complete polite request that matches the current step goal.",
    )


__all__ = [
    "ContextBuilderError",
    "DomainPersistenceError",
    "EmptyTranscriptError",
    "InvalidAudioError",
    "MissingProviderKeyError",
    "GameRuleEngineError",
    "JudgeNodeError",
    "RoleplaySessionTurnError",
    "ResponsePackNodeError",
    "run_roleplay_session_dev_perfect_answer_turn",
    "run_roleplay_session_turn",
    "run_roleplay_session_text_turn",
]
