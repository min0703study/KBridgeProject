from __future__ import annotations

from backend.app.agents.roleplay.logging import log_node_completed
from backend.app.agents.roleplay.schemas import ResponseMessageDraft, ResponsePack
from backend.app.agents.roleplay.state import AgentState


def response_validator_mock_node(state: AgentState) -> AgentState:
    response_pack = state.get("response_pack")
    if response_pack is None or not response_pack.character_dialogue_text:
        state["response_pack"] = ResponsePack(
            message_drafts=[
                ResponseMessageDraft(
                    message_type="roleplay_character_dialogue_text",
                    text_content="네, 알겠습니다.",
                    text_language="ko",
                    translation_json={"en": "Okay, I understand."},
                    step_id=state["current_step"].get("step_id"),
                    scenario_roleplay_character_id=state["character"].get(
                        "scenario_roleplay_character_id"
                    ),
                )
            ],
        )

    log_node_completed(
        "response_validator_mock",
        {
            "response_pack": state["response_pack"],
        },
    )
    return state


def domain_persistence_mock_node(state: AgentState) -> AgentState:
    state["created_turn_id"] = None
    state["created_message_ids"] = []
    log_node_completed(
        "domain_persistence_mock",
        {
            "created_turn_id": state["created_turn_id"],
            "created_message_ids": state["created_message_ids"],
        },
    )
    return state
