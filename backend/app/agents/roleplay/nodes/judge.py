from __future__ import annotations

import json

from google import genai
from google.genai import types
from pydantic import ValidationError

from backend.app.agents.roleplay.logging import log_node_completed, log_node_failed
from backend.app.agents.roleplay.schemas import JudgeResult
from backend.app.agents.roleplay.state import AgentState
from backend.app.core.config import get_settings
from backend.app.services.roleplay_voice_service import MissingProviderKeyError


class JudgeNodeError(RuntimeError):
    status_code = 502


class JudgeNodeProviderError(JudgeNodeError):
    status_code = 503


class JudgeNodeOutputError(JudgeNodeError):
    status_code = 502


JUDGE_SYSTEM_INSTRUCTION = """
You are the Judge Node for a Korean roleplaying learning game.
Your only job is evaluation.

Do not generate a character response.
Do not generate hints.
Do not generate correction sentences.
Do not change game state.
Do not decide step advancement, chances, or session ending.

Evaluate whether the learner input achieves the current step goal.
Prioritize inferred intent over perfect grammar.
If input_method is voice, do not penalize missing question marks or weak punctuation.
For voice/STT input, infer question intent from the step goal, dialogue context, and Korean endings such as 필요하세요, 드릴까요, 있으세요, 하시겠어요, 괜찮으세요.
If the meaning is understandable and the step goal is achieved, return pass or soft_pass.
If the meaning is right but the expression is awkward, blunt, unnatural, or culturally risky, return soft_pass.
If the step goal is not achieved, the meaning is unclear, or the input is off-topic, return fail.

Use selected_knowledge only as reference material. Do not mark a cultural issue merely because knowledge was provided.

Return only valid JSON with exactly these fields:
{
  "evaluation_result": "pass" | "soft_pass" | "fail",
  "confidence": number from 0 to 1,
  "inferred_intent_text": "short explanation of inferred learner intent",
  "step_goal_matched": boolean,
  "communication_success": boolean,
  "issue_tags": ["grammar" | "vocabulary" | "politeness" | "naturalness" | "culturalContext" | "taskExpression" | "clarity" | "offTopic"],
  "correction_needed": boolean,
  "cultural_issue_detected": boolean,
  "evaluation_reason_text": "short reason for the evaluation"
}
""".strip()


def judge_node(state: AgentState) -> AgentState:
    settings = get_settings()
    if not settings.resolved_gemini_api_key:
        raise MissingProviderKeyError("GEMINI_API_KEY or GOOGLE_API_KEY is required.")

    prompt = build_judge_prompt(state)
    client = genai.Client(api_key=settings.resolved_gemini_api_key)

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=JUDGE_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        raise JudgeNodeProviderError(f"Gemini Judge Node failed: {exc}") from exc

    raw_response_text = response.text or ""
    try:
        result = parse_judge_response(raw_response_text)
    except JudgeNodeOutputError as exc:
        log_node_failed(
            "judge",
            {
                "error": str(exc),
                "raw_response_preview": raw_response_text[:4000],
                "raw_response_length": len(raw_response_text),
                "prompt_summary": _build_judge_prompt_summary(
                    state=state,
                    prompt=prompt,
                    model=settings.gemini_model,
                ),
                "fallback": "none",
            },
        )
        raise

    normalized_result = normalize_judge_result(result)
    state["judge_result"] = normalized_result

    log_node_completed(
        "judge",
        {
            "judge_result": normalized_result,
            "selected_knowledge_count": len(state.get("selected_knowledge") or []),
        },
    )
    return state


def build_judge_prompt(state: AgentState) -> str:
    current_step = state["current_step"]
    scenario = state["scenario"]
    scenario_version = state["scenario_version"]
    character = state["character"]
    location = state["location"]

    prompt_payload = {
        "roleplay_session_id": state["roleplay_session_id"],
        "learner_id": state["learner_id"],
        "scenario": {
            "title": scenario.get("title"),
            "description": scenario.get("description"),
            "difficulty": scenario.get("difficulty"),
        },
        "scenario_version": {
            "learning_language": scenario_version.get("learning_language"),
            "default_system_language": scenario_version.get("default_system_language"),
        },
        "step": {
            "step_id": current_step.get("step_id"),
            "step_order": current_step.get("step_order"),
            "step_title": current_step.get("step_title"),
            "step_goal": current_step.get("step_goal"),
            "roleplay_guidance_text": current_step.get("roleplay_guidance_text"),
        },
        "roles_and_location": {
            "learner_role": "roleplay learner",
            "character_role": character.get("role_name"),
            "character_name": character.get("name"),
            "character_description": character.get("description"),
            "character_persona": character.get("persona_prompt"),
            "location_name": location.get("name"),
            "location_description": location.get("description"),
            "location_prompt": location.get("location_prompt"),
        },
        "learner_input_text": state["learner_input_text"],
        "input_method": state["input_method"],
        "recent_messages": [
            {
                "sender_type": message.get("sender_type"),
                "message_type": message.get("message_type"),
                "text_content": message.get("text_content"),
            }
            for message in state.get("recent_messages", [])
        ],
        "step_sample_answers": state.get("step_sample_answers", []),
        "selected_knowledge": [
            {
                "document_id": item.document_id,
                "category": item.category,
                "subject": item.subject,
                "chunk_text": item.chunk_text,
            }
            for item in state.get("selected_knowledge", [])
        ],
        "judge_rules": [
            "Evaluate intent before grammar.",
            "pass means the step goal is clearly achieved with no major expression issue.",
            "soft_pass means the step goal is achieved but expression improvement is needed.",
            "fail means the step goal is not achieved, unclear, or off-topic.",
            "RAG knowledge is reference only, never automatic evidence of a cultural issue.",
            (
                "If input_method is voice, do not penalize obvious Korean STT homophone or spacing "
                "artifacts when the learner's intended meaning is clear. For example, treat '내 총', "
                "'내 결제', or '내 완료' as likely STT artifacts for '네, 총', '네, 결제', or '네, 완료' "
                "instead of learner grammar mistakes."
            ),
        ],
    }

    return json.dumps(prompt_payload, ensure_ascii=False, indent=2)


def _build_judge_prompt_summary(*, state: AgentState, prompt: str, model: str) -> dict:
    current_step = state["current_step"]
    return {
        "model": model,
        "prompt_length": len(prompt),
        "roleplay_session_id": state["roleplay_session_id"],
        "learner_id": state["learner_id"],
        "input_method": state["input_method"],
        "learner_input_preview": (state.get("learner_input_text") or "")[:500],
        "step_id": current_step.get("step_id"),
        "step_order": current_step.get("step_order"),
        "step_title": current_step.get("step_title"),
        "step_goal": current_step.get("step_goal"),
        "selected_knowledge_count": len(state.get("selected_knowledge") or []),
        "recent_message_count": len(state.get("recent_messages") or []),
    }


def parse_judge_response(raw_text: str) -> JudgeResult:
    cleaned_text = raw_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        cleaned_text = cleaned_text.removeprefix("json").strip()

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError as exc:
        raise JudgeNodeOutputError("Judge Node returned invalid JSON.") from exc

    try:
        return JudgeResult.model_validate(parsed)
    except ValidationError as exc:
        raise JudgeNodeOutputError("Judge Node returned JSON that does not match JudgeResult.") from exc


def normalize_judge_result(result: JudgeResult) -> JudgeResult:
    normalized = result.model_copy(deep=True)

    if normalized.evaluation_result == "pass":
        normalized.step_goal_matched = True
        normalized.communication_success = True
        normalized.correction_needed = False

    if normalized.evaluation_result == "soft_pass":
        normalized.step_goal_matched = True
        normalized.communication_success = True
        normalized.correction_needed = True

    if normalized.evaluation_result == "fail":
        normalized.step_goal_matched = False
        normalized.correction_needed = False

    normalized.confidence = max(0.0, min(1.0, normalized.confidence))
    return normalized
