from __future__ import annotations

import re

from backend.app.agents.roleplay.logging import log_node_completed
from backend.app.agents.roleplay.nodes.response_pack import ensure_minimum_response_pack
from backend.app.agents.roleplay.schemas import (
    MessageType,
    ResponsePack,
    ResponseValidationResult,
)
from backend.app.agents.roleplay.state import AgentState


def response_validator_node(state: AgentState) -> AgentState:
    response_pack = state.get("response_pack")
    errors: list[str] = []
    warnings: list[str] = []

    if response_pack is None:
        errors.append("response_pack is missing.")
        response_pack = ResponsePack()

    errors.extend(_validate_required_dialogue(response_pack))
    errors.extend(_validate_languages(state, response_pack))
    errors.extend(_validate_hint_rules(state, response_pack))
    errors.extend(_validate_correction_rules(state, response_pack))
    errors.extend(_validate_step_ids(state, response_pack))
    warnings.extend(_validate_lengths(response_pack))
    warnings.extend(_validate_role_confusion_risk(state, response_pack))

    fallback_used = bool(errors)
    fallback_errors: list[str] = []
    if fallback_used:
        response_pack = ensure_minimum_response_pack(state, ResponsePack())
        fallback_errors.extend(_validate_required_dialogue(response_pack))
        fallback_errors.extend(_validate_languages(state, response_pack))
        fallback_errors.extend(_validate_hint_rules(state, response_pack))
        fallback_errors.extend(_validate_correction_rules(state, response_pack))
        fallback_errors.extend(_validate_step_ids(state, response_pack))
        if fallback_errors:
            errors.extend([f"fallback_error: {error}" for error in fallback_errors])

    validation_result = ResponseValidationResult(
        is_valid=not fallback_errors,
        errors=errors,
        warnings=warnings,
        fallback_used=fallback_used,
    )
    state["response_pack"] = response_pack
    state["response_validation_result"] = validation_result

    log_node_completed(
        "response_validator",
        {
            "response_validation_result": validation_result,
            "response_pack": response_pack,
        },
    )
    return state


def _validate_required_dialogue(response_pack: ResponsePack) -> list[str]:
    if response_pack.character_dialogue_text:
        return []
    return ["roleplay_character_dialogue_text is required."]


def _validate_languages(state: AgentState, response_pack: ResponsePack) -> list[str]:
    learning_language = state["scenario_version"].get("learning_language") or "ko"
    system_language = state["scenario_version"].get("default_system_language") or "en"
    expected_language_by_type: dict[MessageType, str] = {
        "scene_text": system_language,
        "roleplay_character_action_text": system_language,
        "roleplay_character_dialogue_text": learning_language,
        "hint": system_language,
        "correction_feedback": system_language,
    }

    errors: list[str] = []
    for index, draft in enumerate(response_pack.message_drafts):
        expected = expected_language_by_type[draft.message_type]
        if draft.text_language != expected:
            errors.append(
                f"message_drafts[{index}].text_language must be {expected} for {draft.message_type}."
            )
    return errors


def _validate_hint_rules(state: AgentState, response_pack: ResponsePack) -> list[str]:
    rule_decision = state["rule_decision"]
    judge_result = state["judge_result"]
    should_generate_hint = bool(
        rule_decision
        and judge_result
        and rule_decision.progress_outcome in {"stay_current_step", "fail_session"}
        and judge_result.evaluation_result == "fail"
    )

    errors: list[str] = []
    hint_drafts = [
        draft for draft in response_pack.message_drafts if draft.message_type == "hint"
    ]
    if should_generate_hint and not hint_drafts:
        errors.append("hint is required for failed stay/fail_session outcomes.")
    if not should_generate_hint and hint_drafts:
        errors.append("hint must not be generated for this outcome.")

    for index, draft in enumerate(response_pack.message_drafts):
        if draft.message_type != "hint" and draft.hint_level is not None:
            errors.append(f"message_drafts[{index}].hint_level is only allowed on hint messages.")
        if draft.message_type == "hint":
            if draft.hint_level is None:
                errors.append(f"message_drafts[{index}].hint_level is required.")
            elif rule_decision and draft.hint_level != rule_decision.hint_level:
                errors.append(
                    f"message_drafts[{index}].hint_level must match rule_decision.hint_level."
                )
    return errors


def _validate_correction_rules(state: AgentState, response_pack: ResponsePack) -> list[str]:
    judge_result = state["judge_result"]
    should_generate_correction = bool(
        judge_result
        and judge_result.evaluation_result == "soft_pass"
        and judge_result.correction_needed
    )
    has_correction_feedback = any(
        draft.message_type == "correction_feedback"
        for draft in response_pack.message_drafts
    )

    errors: list[str] = []
    if should_generate_correction:
        if not response_pack.correction_items:
            errors.append("correction_items are required for soft_pass correction.")
        if not has_correction_feedback:
            errors.append("correction_feedback is required for soft_pass correction.")
    else:
        if response_pack.correction_items:
            errors.append("correction_items must not be generated for this outcome.")
        if has_correction_feedback:
            errors.append("correction_feedback must not be generated for this outcome.")
    return errors


def _validate_step_ids(state: AgentState, response_pack: ResponsePack) -> list[str]:
    current_step_id = state["current_step"].get("step_id")
    rule_decision = state["rule_decision"]
    allowed_step_ids = {current_step_id}
    if rule_decision and rule_decision.next_step_id:
        allowed_step_ids.add(rule_decision.next_step_id)

    errors: list[str] = []
    for index, draft in enumerate(response_pack.message_drafts):
        if draft.step_id not in allowed_step_ids:
            errors.append(
                f"message_drafts[{index}].step_id must be current_step_id or next_step_id."
            )
    return errors


def _validate_lengths(response_pack: ResponsePack) -> list[str]:
    warnings: list[str] = []
    for index, draft in enumerate(response_pack.message_drafts):
        if len(draft.text_content) > 500:
            warnings.append(f"message_drafts[{index}].text_content is long.")
    return warnings


def _validate_role_confusion_risk(state: AgentState, response_pack: ResponsePack) -> list[str]:
    learner_texts = [state.get("learner_input_text") or ""]
    learner_texts.extend(state.get("step_sample_answers") or [])
    normalized_learner_texts = {
        normalized for text in learner_texts if (normalized := _normalize_role_text(text))
    }

    warnings: list[str] = []
    for index, draft in enumerate(response_pack.message_drafts):
        if draft.message_type != "roleplay_character_dialogue_text":
            continue

        normalized_dialogue = _normalize_role_text(draft.text_content)
        if normalized_dialogue and normalized_dialogue in normalized_learner_texts:
            warnings.append(
                f"message_drafts[{index}].text_content may repeat learner-role text."
            )

    return warnings


def _normalize_role_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").casefold()
