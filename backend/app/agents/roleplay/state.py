from __future__ import annotations

from typing import Any, TypedDict

from backend.app.agents.roleplay.schemas import (
    FinalFeedbackResult,
    InputMethod,
    JudgeResult,
    PersistenceResult,
    ResponsePack,
    ResponseValidationResult,
    RetrievedKnowledge,
    RuleDecision,
)


class AgentState(TypedDict):
    roleplay_session_id: str
    learner_id: str
    learner_input_text: str
    input_method: InputMethod

    session: dict[str, Any]
    scenario_version: dict[str, Any]
    scenario: dict[str, Any]
    current_step: dict[str, Any]
    next_step: dict[str, Any] | None
    character: dict[str, Any]
    location: dict[str, Any]
    recent_messages: list[dict[str, Any]]
    step_sample_answers: list[str]

    last_character_message_text: str | None
    last_learner_message_text: str | None

    retrieved_candidates: list[RetrievedKnowledge]
    selected_knowledge: list[RetrievedKnowledge]

    judge_result: JudgeResult | None
    rule_decision: RuleDecision | None
    response_pack: ResponsePack | None
    response_validation_result: ResponseValidationResult | None
    persistence_result: PersistenceResult | None
    final_feedback_result: FinalFeedbackResult | None

    created_turn_id: str | None
    created_message_ids: list[str]
    created_evaluation_id: str | None


def build_initial_state(
    *,
    roleplay_session_id: str,
    learner_id: str,
    learner_input_text: str,
    input_method: InputMethod,
) -> AgentState:
    return {
        "roleplay_session_id": roleplay_session_id,
        "learner_id": learner_id,
        "learner_input_text": learner_input_text,
        "input_method": input_method,
        "session": {},
        "scenario_version": {},
        "scenario": {},
        "current_step": {},
        "next_step": None,
        "character": {},
        "location": {},
        "recent_messages": [],
        "step_sample_answers": [],
        "last_character_message_text": None,
        "last_learner_message_text": None,
        "retrieved_candidates": [],
        "selected_knowledge": [],
        "judge_result": None,
        "rule_decision": None,
        "response_pack": None,
        "response_validation_result": None,
        "persistence_result": None,
        "final_feedback_result": None,
        "created_turn_id": None,
        "created_message_ids": [],
        "created_evaluation_id": None,
    }
