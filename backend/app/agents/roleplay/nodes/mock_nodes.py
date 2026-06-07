from __future__ import annotations

from backend.app.agents.roleplay.schemas import (
    CorrectionItem,
    JudgeResult,
    ResponsePack,
    RuleDecision,
)
from backend.app.agents.roleplay.state import AgentState


def judge_mock_node(state: AgentState) -> AgentState:
    learner_input = state.get("learner_input_text", "").strip()
    selected_knowledge = state.get("selected_knowledge") or []

    if not learner_input:
        state["judge_result"] = JudgeResult(
            evaluation_result="fail",
            confidence=1.0,
            inferred_intent_text="No learner input was provided.",
            step_goal_matched=False,
            communication_success=False,
            issue_tags=["taskExpression"],
            correction_needed=False,
            cultural_issue_detected=False,
            evaluation_reason_text="The MVP mock judge fails empty input.",
        )
        return state

    state["judge_result"] = JudgeResult(
        evaluation_result="soft_pass",
        confidence=0.72,
        inferred_intent_text="The learner is attempting to respond to the current roleplay step.",
        step_goal_matched=True,
        communication_success=True,
        issue_tags=["politeness", "naturalness"],
        correction_needed=True,
        cultural_issue_detected=bool(selected_knowledge),
        evaluation_reason_text="The MVP mock judge accepts non-empty input as soft_pass.",
    )
    return state


def rule_engine_mock_node(state: AgentState) -> AgentState:
    judge_result = state["judge_result"]
    session = state["session"]
    is_fail = judge_result is not None and judge_result.evaluation_result == "fail"

    state["rule_decision"] = RuleDecision(
        should_advance_step=False,
        should_decrease_chance=False,
        should_end_session=False,
        next_step_id=None,
        remaining_chances_after=int(session.get("remaining_chances") or 0),
        end_status_after=session.get("end_status") or "in_progress",
        hint_level="light" if is_fail else "none",
    )
    return state


def response_pack_mock_node(state: AgentState) -> AgentState:
    judge_result = state["judge_result"]
    learner_input = state.get("learner_input_text") or ""

    if judge_result and judge_result.evaluation_result == "fail":
        state["response_pack"] = ResponsePack(
            character_dialogue_text="다시 한 번 말씀해 주시겠어요?",
            character_dialogue_translation_text="Could you try saying that again?",
            hint_text="손님에게 필요한 정보를 공손하게 요청해 보세요.",
        )
        return state

    state["response_pack"] = ResponsePack(
        character_dialogue_text="네, 신분증 여기 있습니다.",
        character_dialogue_translation_text="Sure, here is my ID.",
        correction_items=[
            CorrectionItem(
                type="politeness",
                original_text=learner_input,
                corrected_text="죄송하지만, 신분증 확인 부탁드립니다.",
                reason_text="A softer request sounds more polite in a service situation.",
            )
        ],
    )
    return state


def response_validator_mock_node(state: AgentState) -> AgentState:
    response_pack = state.get("response_pack")
    if response_pack is None or not response_pack.character_dialogue_text:
        state["response_pack"] = ResponsePack(
            character_dialogue_text="네, 알겠습니다.",
            character_dialogue_translation_text="Okay, I understand.",
        )
    return state


def domain_persistence_mock_node(state: AgentState) -> AgentState:
    state["created_turn_id"] = None
    state["created_message_ids"] = []
    return state
