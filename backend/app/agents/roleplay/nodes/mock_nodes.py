from __future__ import annotations

from backend.app.agents.roleplay.schemas import (
    CorrectionItem,
    ResponsePack,
    RuleDecision,
)
from backend.app.agents.roleplay.state import AgentState


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
    print(
        "[RoleplayAgent] node=rule_engine_mock completed "
        f"remaining_chances_after={state['rule_decision'].remaining_chances_after} "
        f"end_status_after={state['rule_decision'].end_status_after} "
        f"hint_level={state['rule_decision'].hint_level}"
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
        print(
            "[RoleplayAgent] node=response_pack_mock completed "
            "dialogue=True hint=True corrections=0"
        )
        return state

    if judge_result and not judge_result.correction_needed:
        state["response_pack"] = ResponsePack(
            character_dialogue_text="네, 알겠습니다.",
            character_dialogue_translation_text="Okay, I understand.",
        )
        print(
            "[RoleplayAgent] node=response_pack_mock completed "
            "dialogue=True hint=False corrections=0"
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
    print(
        "[RoleplayAgent] node=response_pack_mock completed "
        f"dialogue={bool(state['response_pack'].character_dialogue_text)} "
        f"hint={bool(state['response_pack'].hint_text)} "
        f"corrections={len(state['response_pack'].correction_items)}"
    )
    return state


def response_validator_mock_node(state: AgentState) -> AgentState:
    response_pack = state.get("response_pack")
    if response_pack is None or not response_pack.character_dialogue_text:
        state["response_pack"] = ResponsePack(
            character_dialogue_text="네, 알겠습니다.",
            character_dialogue_translation_text="Okay, I understand.",
        )
    print(
        "[RoleplayAgent] node=response_validator_mock completed "
        f"dialogue={bool(state['response_pack'].character_dialogue_text)}"
    )
    return state


def domain_persistence_mock_node(state: AgentState) -> AgentState:
    state["created_turn_id"] = None
    state["created_message_ids"] = []
    print(
        "[RoleplayAgent] node=domain_persistence_mock completed "
        "created_turn_id=None created_message_ids=0"
    )
    return state
