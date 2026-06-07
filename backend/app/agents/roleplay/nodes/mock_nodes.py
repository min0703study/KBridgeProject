from __future__ import annotations

from backend.app.agents.roleplay.schemas import CorrectionItem, ResponsePack
from backend.app.agents.roleplay.state import AgentState


def response_pack_mock_node(state: AgentState) -> AgentState:
    judge_result = state["judge_result"]
    rule_decision = state["rule_decision"]
    learner_input = state.get("learner_input_text") or ""

    if rule_decision and rule_decision.progress_outcome in {"stay_current_step", "fail_session"}:
        hint_text = {
            "light": "현재 단계 목표를 다시 떠올려 보세요.",
            "medium": "손님에게 필요한 정보를 공손하게 요청해 보세요.",
            "strong": "예시 표현처럼 정중하게 질문하는 구조를 사용해 보세요.",
        }.get(rule_decision.hint_level, "현재 단계 목표에 맞게 다시 말해 보세요.")
        state["response_pack"] = ResponsePack(
            character_dialogue_text="다시 한 번 말씀해 주시겠어요?"
            if rule_decision.progress_outcome == "stay_current_step"
            else "괜찮습니다. 여기서 마무리할게요.",
            character_dialogue_translation_text="Could you try saying that again?"
            if rule_decision.progress_outcome == "stay_current_step"
            else "It's okay. Let's wrap up here.",
            hint_text=hint_text,
        )
        print(
            "[RoleplayAgent] node=response_pack_mock completed "
            f"outcome={rule_decision.progress_outcome} "
            f"hint_level={rule_decision.hint_level} corrections=0"
        )
        return state

    if rule_decision and rule_decision.progress_outcome == "complete_session":
        state["response_pack"] = ResponsePack(
            character_dialogue_text="좋아요, 감사합니다.",
            character_dialogue_translation_text="Great, thank you.",
        )
        print(
            "[RoleplayAgent] node=response_pack_mock completed "
            "outcome=complete_session hint=False corrections=0"
        )
        return state

    if judge_result and not judge_result.correction_needed:
        state["response_pack"] = ResponsePack(
            character_dialogue_text="네, 알겠습니다.",
            character_dialogue_translation_text="Okay, I understand.",
        )
        print(
            "[RoleplayAgent] node=response_pack_mock completed "
            f"outcome={rule_decision.progress_outcome if rule_decision else None} "
            "hint=False corrections=0"
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
        f"outcome={rule_decision.progress_outcome if rule_decision else None} "
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
