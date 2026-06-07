from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.roleplay.logging import log_node_completed
from backend.app.agents.roleplay.schemas import (
    PersistedTurnMessage,
    PersistenceResult,
    ResponseMessageDraft,
)
from backend.app.agents.roleplay.state import AgentState
from backend.app.db.models import (
    Message,
    RoleplayEvaluation,
    RoleplaySession,
    RoleplayTurn,
)


class DomainPersistenceError(RuntimeError):
    status_code = 500


def make_domain_persistence_node(session: AsyncSession):
    async def domain_persistence_node(state: AgentState) -> AgentState:
        rule_decision = state["rule_decision"]
        judge_result = state["judge_result"]
        response_pack = state["response_pack"]
        if rule_decision is None or judge_result is None or response_pack is None:
            raise DomainPersistenceError(
                "Rule decision, judge result, and response pack are required before persistence."
            )

        now = datetime.now(UTC)
        roleplay_session_id = _uuid(state["roleplay_session_id"])
        current_step_id = _uuid(state["current_step"]["step_id"])
        next_step_id = _uuid(rule_decision.next_step_id) if rule_decision.next_step_id else None

        try:
            turn_order = await _next_order(
                session,
                RoleplayTurn.turn_order,
                RoleplayTurn.roleplay_session_id == roleplay_session_id,
            )
            message_order = await _next_order(
                session,
                Message.message_order,
                Message.roleplay_session_id == roleplay_session_id,
            )
            evaluation_order = await _next_order(
                session,
                RoleplayEvaluation.evaluation_order,
                RoleplayEvaluation.roleplay_session_id == roleplay_session_id,
            )

            roleplay_turn = RoleplayTurn(
                roleplay_turn_id=uuid4(),
                roleplay_session_id=roleplay_session_id,
                step_id=current_step_id,
                next_step_id=next_step_id,
                turn_order=turn_order,
                input_method=state["input_method"],
                remaining_chances_before=rule_decision.remaining_chances_before,
                remaining_chances_after=rule_decision.remaining_chances_after,
                end_status_after=rule_decision.end_status_after,
                created_at=now,
                fail_count_before=rule_decision.current_step_fail_count_before,
                fail_count_after=rule_decision.current_step_fail_count_after,
            )
            session.add(roleplay_turn)
            await session.flush()

            created_messages: list[Message] = []
            learner_message = Message(
                message_id=uuid4(),
                roleplay_session_id=roleplay_session_id,
                roleplay_turn_id=roleplay_turn.roleplay_turn_id,
                step_id=current_step_id,
                scenario_roleplay_character_id=None,
                message_order=message_order,
                sender_type="learner",
                generated_by=None,
                message_type="learner_input_text",
                text_content=state["learner_input_text"],
                text_language=state["scenario_version"].get("learning_language") or "ko",
                translation_json=None,
                audio_file_id=None,
                created_at=now,
                hint_level=None,
            )
            session.add(learner_message)
            created_messages.append(learner_message)
            message_order += 1

            for draft in response_pack.message_drafts:
                message = _message_from_draft(
                    draft=draft,
                    roleplay_session_id=roleplay_session_id,
                    roleplay_turn_id=roleplay_turn.roleplay_turn_id,
                    message_order=message_order,
                    created_at=now,
                    fallback_character_id=state["character"].get(
                        "scenario_roleplay_character_id"
                    ),
                )
                session.add(message)
                created_messages.append(message)
                message_order += 1

            roleplay_evaluation = RoleplayEvaluation(
                roleplay_evaluation_id=uuid4(),
                roleplay_turn_id=roleplay_turn.roleplay_turn_id,
                roleplay_session_id=roleplay_session_id,
                step_id=current_step_id,
                evaluation_order=evaluation_order,
                learner_input_text=state["learner_input_text"],
                evaluation_result=judge_result.evaluation_result,
                inferred_intent_text=judge_result.inferred_intent_text,
                step_goal_matched=judge_result.step_goal_matched,
                evaluation_reason_text=judge_result.evaluation_reason_text,
                correction_json=[
                    item.model_dump(mode="json")
                    for item in response_pack.correction_items
                ]
                or None,
                cultural_issue_detected=judge_result.cultural_issue_detected,
                should_advance_step=rule_decision.should_advance_step,
                should_decrease_chance=rule_decision.should_decrease_chance,
                should_end_session=rule_decision.should_end_session,
                created_at=now,
            )
            session.add(roleplay_evaluation)

            roleplay_session = await session.get(RoleplaySession, roleplay_session_id)
            if roleplay_session is None:
                raise DomainPersistenceError("Roleplay session was not found for persistence.")
            roleplay_session.current_step_id = (
                next_step_id
                if rule_decision.progress_outcome == "advance_to_next_step" and next_step_id
                else roleplay_session.current_step_id
            )
            roleplay_session.remaining_chances = rule_decision.remaining_chances_after
            roleplay_session.current_step_fail_count = (
                rule_decision.current_step_fail_count_after
            )
            roleplay_session.end_status = rule_decision.end_status_after
            roleplay_session.ended_at = now if rule_decision.should_end_session else None
            roleplay_session.updated_at = now

            await session.commit()
            await session.refresh(roleplay_session)
        except Exception:
            await session.rollback()
            raise

        persisted_messages = [
            _serialize_persisted_message(message) for message in created_messages
        ]
        session_after = {
            "roleplay_session_id": str(roleplay_session.roleplay_session_id),
            "current_step_id": str(roleplay_session.current_step_id)
            if roleplay_session.current_step_id
            else None,
            "remaining_chances": roleplay_session.remaining_chances,
            "end_status": roleplay_session.end_status,
            "current_step_fail_count": roleplay_session.current_step_fail_count,
            "ended_at": roleplay_session.ended_at.isoformat()
            if roleplay_session.ended_at
            else None,
        }
        persistence_result = PersistenceResult(
            created_turn_id=str(roleplay_turn.roleplay_turn_id),
            created_message_ids=[str(message.message_id) for message in created_messages],
            created_evaluation_id=str(roleplay_evaluation.roleplay_evaluation_id),
            session_after=session_after,
            turn_messages=persisted_messages,
        )

        state["created_turn_id"] = persistence_result.created_turn_id
        state["created_message_ids"] = persistence_result.created_message_ids
        state["created_evaluation_id"] = persistence_result.created_evaluation_id
        state["persistence_result"] = persistence_result
        state["session"].update(session_after)

        log_node_completed(
            "domain_persistence",
            {
                "persistence_result": persistence_result,
            },
        )
        return state

    return domain_persistence_node


async def _next_order(session: AsyncSession, column, where_clause) -> int:
    result = await session.execute(select(func.coalesce(func.max(column), 0)).where(where_clause))
    return int(result.scalar_one()) + 1


def _message_from_draft(
    *,
    draft: ResponseMessageDraft,
    roleplay_session_id: UUID,
    roleplay_turn_id: UUID,
    message_order: int,
    created_at: datetime,
    fallback_character_id: str | None,
) -> Message:
    sender_type = _sender_type_for_message_type(draft.message_type)
    scenario_character_id = draft.scenario_roleplay_character_id
    if sender_type == "roleplay_character" and not scenario_character_id:
        scenario_character_id = fallback_character_id

    return Message(
        message_id=uuid4(),
        roleplay_session_id=roleplay_session_id,
        roleplay_turn_id=roleplay_turn_id,
        step_id=_uuid(draft.step_id) if draft.step_id else None,
        scenario_roleplay_character_id=_uuid(scenario_character_id)
        if scenario_character_id
        else None,
        message_order=message_order,
        sender_type=sender_type,
        generated_by="ai_agent",
        message_type=draft.message_type,
        text_content=draft.text_content,
        text_language=draft.text_language,
        translation_json=draft.translation_json,
        audio_file_id=None,
        created_at=created_at,
        hint_level=draft.hint_level,
    )


def _sender_type_for_message_type(message_type: str) -> str:
    if message_type in {"scene_text", "hint", "correction_feedback"}:
        return "system"
    if message_type in {
        "roleplay_character_action_text",
        "roleplay_character_dialogue_text",
    }:
        return "roleplay_character"
    return "learner"


def _serialize_persisted_message(message: Message) -> PersistedTurnMessage:
    return PersistedTurnMessage(
        message_id=str(message.message_id),
        sender_type=message.sender_type,
        message_type=message.message_type,
        text_content=message.text_content,
        text_language=message.text_language,
        translation_json=message.translation_json,
        step_id=str(message.step_id) if message.step_id else None,
        scenario_roleplay_character_id=str(message.scenario_roleplay_character_id)
        if message.scenario_roleplay_character_id
        else None,
        message_order=message.message_order,
        hint_level=message.hint_level,
    )


def _uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)
