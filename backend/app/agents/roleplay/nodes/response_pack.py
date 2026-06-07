from __future__ import annotations

import json
from uuid import UUID

from google import genai
from google.genai import types
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.roleplay.logging import log_node_completed
from backend.app.agents.roleplay.schemas import (
    CorrectionItem,
    ResponseMessageDraft,
    ResponsePack,
)
from backend.app.agents.roleplay.state import AgentState
from backend.app.core.config import get_settings
from backend.app.db.models import Step
from backend.app.services.roleplay_voice_service import MissingProviderKeyError


class ResponsePackNodeError(RuntimeError):
    status_code = 502


class ResponsePackProviderError(ResponsePackNodeError):
    status_code = 503


class ResponsePackOutputError(ResponsePackNodeError):
    status_code = 502


RESPONSE_PACK_SYSTEM_INSTRUCTION = """
You are the Response Pack Node for a Korean roleplaying learning game.
Your only job is to generate displayable message drafts for this single turn.

Do not evaluate learner input.
Do not change or reinterpret the Judge result.
Do not decide step advancement, chances, fail counts, or session ending.
Do not write to the database.
Do not generate TTS.
Do not generate final overall learning feedback.

Use rule_decision as the source of truth for progress.
Use judge_result as the source of truth for evaluation and correction need.
Keep character dialogue short, natural, and in persona.
Do not reveal the exact answer the learner should say next.

Return only valid JSON with exactly these top-level fields:
{
  "message_drafts": [
    {
      "message_type": "scene_text" | "roleplay_character_action_text" | "roleplay_character_dialogue_text" | "hint" | "correction_feedback",
      "text_content": "message text",
      "text_language": "en" | "ko",
      "translation_json": {"en": "optional English translation"} | null,
      "step_id": "uuid string or null",
      "scenario_roleplay_character_id": "uuid string or null",
      "hint_level": "light" | "medium" | "strong" | null
    }
  ],
  "correction_items": [
    {
      "type": "grammar" | "vocabulary" | "politeness" | "naturalness" | "culturalContext" | "taskExpression" | "clarity" | "offTopic",
      "original_text": "learner text",
      "corrected_text": "better expression",
      "reason_text": "short explanation"
    }
  ]
}
""".strip()


def make_response_pack_node(session: AsyncSession):
    async def response_pack_node(state: AgentState) -> AgentState:
        settings = get_settings()
        if not settings.resolved_gemini_api_key:
            raise MissingProviderKeyError("GEMINI_API_KEY or GOOGLE_API_KEY is required.")

        rule_decision = state["rule_decision"]
        if rule_decision is None:
            raise ResponsePackNodeError("Rule decision is required before Response Pack Node.")

        if rule_decision.next_step_id:
            state["next_step"] = await _load_next_step(session, rule_decision.next_step_id)
        else:
            state["next_step"] = None

        prompt = build_response_pack_prompt(state)
        client = genai.Client(api_key=settings.resolved_gemini_api_key)

        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=RESPONSE_PACK_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:
            raise ResponsePackProviderError(f"Gemini Response Pack Node failed: {exc}") from exc

        response_pack = parse_response_pack_response(response.text or "")
        response_pack = ensure_minimum_response_pack(state, response_pack)
        state["response_pack"] = response_pack

        log_node_completed(
            "response_pack",
            {
                "next_step": state.get("next_step"),
                "response_pack": response_pack,
            },
        )
        return state

    return response_pack_node


async def _load_next_step(session: AsyncSession, next_step_id: str) -> dict:
    result = await session.execute(select(Step).where(Step.step_id == UUID(next_step_id)))
    step = result.scalar_one_or_none()
    if step is None:
        raise ResponsePackNodeError("Next step was not found.")
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


def build_response_pack_prompt(state: AgentState) -> str:
    scenario_version = state["scenario_version"]
    current_step = state["current_step"]
    next_step = state.get("next_step")
    judge_result = state["judge_result"]
    rule_decision = state["rule_decision"]

    prompt_payload = {
        "roleplay_session_id": state["roleplay_session_id"],
        "learner_id": state["learner_id"],
        "languages": {
            "learning_language": scenario_version.get("learning_language"),
            "system_language": scenario_version.get("default_system_language"),
            "rules": {
                "roleplay_character_dialogue_text": "learning_language",
                "scene_text": "system_language",
                "roleplay_character_action_text": "system_language",
                "hint": "system_language",
                "correction_feedback": "system_language",
            },
        },
        "scenario": state["scenario"],
        "current_step": current_step,
        "next_step": next_step,
        "character": state["character"],
        "location": state["location"],
        "recent_messages": state.get("recent_messages", []),
        "learner_input_text": state["learner_input_text"],
        "judge_result": judge_result.model_dump(mode="json") if judge_result else None,
        "rule_decision": rule_decision.model_dump(mode="json") if rule_decision else None,
        "selected_knowledge": [
            item.model_dump(mode="json") for item in state.get("selected_knowledge", [])
        ],
        "generation_rules": _generation_rules_for_state(state),
    }
    return json.dumps(prompt_payload, ensure_ascii=False, indent=2)


def _generation_rules_for_state(state: AgentState) -> list[str]:
    judge_result = state["judge_result"]
    rule_decision = state["rule_decision"]
    if rule_decision is None:
        return []

    rules = [
        "message_type values must use snake_case DB enum values.",
        "hint_level may appear only on hint messages.",
        "Do not include message_order, roleplay_turn_id, message_id, created_at, audio_file_id, or generated_by.",
    ]

    if rule_decision.progress_outcome in {"stay_current_step", "fail_session"}:
        rules.extend(
            [
                "Generate a hint message because the learner failed and stays or ends.",
                f"The hint message hint_level must be {rule_decision.hint_level}.",
                "Use current_step.step_id for every generated message.",
                "Generate a short character dialogue that re-guides the learner without giving the exact answer.",
            ]
        )
    elif rule_decision.progress_outcome == "advance_to_next_step":
        rules.extend(
            [
                "Do not generate a hint.",
                "Use next_step.step_id for next-step scene/action/dialogue messages.",
                "Generate a short character dialogue that naturally enters the next step.",
            ]
        )
    elif rule_decision.progress_outcome == "complete_session":
        rules.extend(
            [
                "Do not generate a hint.",
                "Generate only a concise completion response, not final feedback.",
            ]
        )

    if judge_result and judge_result.evaluation_result == "soft_pass" and judge_result.correction_needed:
        rules.extend(
            [
                "Generate correction_items.",
                "Generate one correction_feedback message in the system language.",
                "Use current_step.step_id for correction_feedback.",
            ]
        )
    else:
        rules.append("Do not generate correction_items or correction_feedback.")

    return rules


def parse_response_pack_response(raw_text: str) -> ResponsePack:
    cleaned_text = raw_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        cleaned_text = cleaned_text.removeprefix("json").strip()

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError as exc:
        raise ResponsePackOutputError("Response Pack Node returned invalid JSON.") from exc

    try:
        return ResponsePack.model_validate(parsed)
    except ValidationError as exc:
        raise ResponsePackOutputError(
            "Response Pack Node returned JSON that does not match ResponsePack."
        ) from exc


def ensure_minimum_response_pack(state: AgentState, response_pack: ResponsePack) -> ResponsePack:
    rule_decision = state["rule_decision"]
    judge_result = state["judge_result"]
    if rule_decision is None:
        return response_pack

    drafts = list(response_pack.message_drafts)
    has_dialogue = any(
        draft.message_type == "roleplay_character_dialogue_text" for draft in drafts
    )
    has_hint = any(draft.message_type == "hint" for draft in drafts)
    has_correction_feedback = any(
        draft.message_type == "correction_feedback" for draft in drafts
    )

    if rule_decision.progress_outcome in {"stay_current_step", "fail_session"} and not has_hint:
        drafts.insert(0, _fallback_hint_draft(state))

    if (
        judge_result
        and judge_result.evaluation_result == "soft_pass"
        and judge_result.correction_needed
        and not has_correction_feedback
    ):
        drafts.insert(0, _fallback_correction_feedback_draft(state))

    if not has_dialogue:
        drafts.append(_fallback_dialogue_draft(state))

    correction_items = list(response_pack.correction_items)
    if (
        judge_result
        and judge_result.evaluation_result == "soft_pass"
        and judge_result.correction_needed
        and not correction_items
    ):
        correction_items.append(
            CorrectionItem(
                type=(judge_result.issue_tags[0] if judge_result.issue_tags else "naturalness"),
                original_text=state.get("learner_input_text") or "",
                corrected_text=_fallback_corrected_text(state),
                reason_text="This sounds more natural and polite for the current roleplay step.",
            )
        )

    return ResponsePack(message_drafts=drafts, correction_items=correction_items)


def _fallback_hint_draft(state: AgentState) -> ResponseMessageDraft:
    rule_decision = state["rule_decision"]
    current_step = state["current_step"]
    level = rule_decision.hint_level if rule_decision else "light"
    text_by_level = {
        "light": "Try again. Think about the goal of this step.",
        "medium": "Try again. Include the key request or response needed in this situation.",
        "strong": "Try again using a polite request that closely matches the step goal.",
    }
    return ResponseMessageDraft(
        message_type="hint",
        text_content=text_by_level.get(level, text_by_level["light"]),
        text_language=_system_language(state),
        step_id=current_step.get("step_id"),
        hint_level=level if level != "none" else "light",
    )


def _fallback_correction_feedback_draft(state: AgentState) -> ResponseMessageDraft:
    current_step = state["current_step"]
    corrected = _fallback_corrected_text(state)
    return ResponseMessageDraft(
        message_type="correction_feedback",
        text_content=f"Good job. A more natural way to say it is: \"{corrected}\"",
        text_language=_system_language(state),
        step_id=current_step.get("step_id"),
    )


def _fallback_dialogue_draft(state: AgentState) -> ResponseMessageDraft:
    rule_decision = state["rule_decision"]
    step_id = _target_step_id_for_dialogue(state)
    if rule_decision and rule_decision.progress_outcome == "complete_session":
        text = "좋아요. 역할극을 마쳤습니다."
        translation = "Good. The roleplay is complete."
    elif rule_decision and rule_decision.progress_outcome == "fail_session":
        text = "괜찮습니다. 여기서 마무리할게요."
        translation = "It's okay. Let's wrap up here."
    elif rule_decision and rule_decision.progress_outcome == "stay_current_step":
        text = "다시 한 번 말해 주세요."
        translation = "Please say it one more time."
    else:
        text = "좋아요. 계속해 볼게요."
        translation = "Good. Let's continue."

    return ResponseMessageDraft(
        message_type="roleplay_character_dialogue_text",
        text_content=text,
        text_language=_learning_language(state),
        translation_json={_system_language(state): translation},
        step_id=step_id,
        scenario_roleplay_character_id=state["character"].get("scenario_roleplay_character_id"),
    )


def _fallback_corrected_text(state: AgentState) -> str:
    samples = state.get("step_sample_answers") or []
    if samples:
        return samples[0]
    return state.get("learner_input_text") or ""


def _target_step_id_for_dialogue(state: AgentState) -> str | None:
    rule_decision = state["rule_decision"]
    if (
        rule_decision
        and rule_decision.progress_outcome == "advance_to_next_step"
        and rule_decision.next_step_id
    ):
        return rule_decision.next_step_id
    return state["current_step"].get("step_id")


def _learning_language(state: AgentState) -> str:
    return state["scenario_version"].get("learning_language") or "ko"


def _system_language(state: AgentState) -> str:
    return state["scenario_version"].get("default_system_language") or "en"
