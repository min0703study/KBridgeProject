from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.roleplay.graph import build_roleplay_turn_graph
from backend.app.agents.roleplay.nodes.context_builder import ContextBuilderError
from backend.app.agents.roleplay.nodes.domain_persistence import DomainPersistenceError
from backend.app.agents.roleplay.nodes.game_rule_engine import GameRuleEngineError
from backend.app.agents.roleplay.nodes.judge import JudgeNodeError
from backend.app.agents.roleplay.nodes.response_pack import ResponsePackNodeError
from backend.app.agents.roleplay.schemas import CorrectionItem, ResponsePack
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
    graph = build_roleplay_turn_graph(session)
    final_state = await graph.ainvoke(
        build_initial_state(
            roleplay_session_id=str(parsed_session_id),
            learner_id=str(learner_id),
            learner_input_text=transcript,
            input_method="voice",
        )
    )

    response_pack: ResponsePack = final_state["response_pack"]
    assistant_ko = response_pack.character_dialogue_text or "네, 알겠습니다."
    audio_base64 = text_to_speech_base64(assistant_ko)
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
    "run_roleplay_session_turn",
]
