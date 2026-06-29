from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import streamlit as st

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - the UI shows a clear fallback state.
    genai = None
    types = None

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - sequential fallback keeps the sample usable.
    END = START = StateGraph = None

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[2]
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import sample_roleplaying_db as sample_db


LEARNER_ID = "23978a46-2c8e-4e2c-aa1d-4c37380b436e"
INPUT_METHOD = "text"
NODE_SEQUENCE = [
    "context_builder",
    "judge",
    "game_rule_engine",
    "response_pack",
    "response_validator",
    "domain_persistence",
]

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
If the meaning is understandable and the step goal is achieved, return pass or soft_pass.
If the meaning is right but the expression is awkward, blunt, unnatural, or culturally risky, return soft_pass.
If the step goal is not achieved, the meaning is unclear, or the input is off-topic, return fail.

Do not mark a cultural issue unless the learner input clearly contains one.

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
Never confuse the roles in the roleplay.
The roleplay_character must speak and act only as the assigned character.
The roleplay_character must not speak as the learner/user.
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

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_dotenv_value(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")
    return None


def api_key() -> str | None:
    return load_dotenv_value("GEMINI_API_KEY") or load_dotenv_value("GOOGLE_API_KEY")


def gemini_model() -> str:
    return load_dotenv_value("GEMINI_MODEL") or "gemini-2.5-flash"


def parse_json_maybe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items() if not str(key).startswith("_")}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    return value


def compact_json(value: Any) -> str:
    return json.dumps(json_safe(value), ensure_ascii=False, indent=2)


def ensure_runtime_tables() -> None:
    for name in [
        "ROLEPLAY_SESSIONS",
        "ROLEPLAY_TURNS",
        "MESSAGES",
        "ROLEPLAY_EVALUATIONS",
    ]:
        if not hasattr(sample_db, name):
            setattr(sample_db, name, [])


def sorted_steps() -> list[dict[str, Any]]:
    return sorted(sample_db.STEPS, key=lambda item: int(item["step_order"]))


def first_scenario_version() -> dict[str, Any]:
    versions = sorted(
        sample_db.SCENARIO_VERSIONS,
        key=lambda item: (
            item.get("status") != "published",
            item.get("published_at") or "",
            item.get("created_at") or "",
        ),
        reverse=False,
    )
    return versions[0]


def find_one(table: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    for item in table:
        if str(item.get(key)) == str(value):
            return item
    raise LookupError(f"{key}={value} was not found.")


def find_next_step(scenario_version_id: str, current_step_order: int) -> dict[str, Any] | None:
    for step in sorted_steps():
        if (
            str(step["scenario_version_id"]) == str(scenario_version_id)
            and int(step["step_order"]) > current_step_order
        ):
            return step
    return None


def reset_fake_db() -> str:
    ensure_runtime_tables()
    sample_db.ROLEPLAY_SESSIONS.clear()
    sample_db.ROLEPLAY_TURNS.clear()
    sample_db.MESSAGES.clear()
    sample_db.ROLEPLAY_EVALUATIONS.clear()

    version = first_scenario_version()
    first_step = sorted_steps()[0]
    session_id = str(uuid4())
    session = {
        "roleplay_session_id": session_id,
        "learner_id": LEARNER_ID,
        "scenario_version_id": version["scenario_version_id"],
        "current_step_id": first_step["step_id"],
        "total_chances": version["default_total_chances"],
        "remaining_chances": version["default_total_chances"],
        "end_status": "in_progress",
        "started_at": now_iso(),
        "ended_at": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "current_step_fail_count": 0,
    }
    sample_db.ROLEPLAY_SESSIONS.append(session)
    add_initial_step_messages(session_id, first_step)
    return session_id


def add_initial_step_messages(session_id: str, step: dict[str, Any]) -> None:
    order = next_message_order(session_id)
    initial_messages = [
        ("system", "system", "scene_text", step.get("initial_scene_text"), "en", None),
        (
            "roleplay_character",
            "admin",
            "roleplay_character_action_text",
            step.get("initial_roleplay_character_action_text"),
            "en",
            None,
        ),
        (
            "roleplay_character",
            "admin",
            "roleplay_character_dialogue_text",
            step.get("initial_roleplay_character_dialogue_text"),
            step.get("initial_roleplay_character_dialogue_language") or "ko",
            parse_json_maybe(step.get("initial_roleplay_character_dialogue_translation_json")),
        ),
    ]
    for sender_type, generated_by, message_type, text, language, translation in initial_messages:
        if not text:
            continue
        sample_db.MESSAGES.append(
            {
                "message_id": str(uuid4()),
                "roleplay_session_id": session_id,
                "roleplay_turn_id": None,
                "step_id": step["step_id"],
                "scenario_roleplay_character_id": step.get("primary_scenario_roleplay_character_id"),
                "message_order": order,
                "sender_type": sender_type,
                "generated_by": generated_by,
                "message_type": message_type,
                "text_content": text,
                "text_language": language,
                "translation_json": translation,
                "audio_file_id": None,
                "created_at": now_iso(),
                "hint_level": None,
            }
        )
        order += 1


def next_message_order(session_id: str) -> int:
    orders = [
        int(message["message_order"])
        for message in sample_db.MESSAGES
        if message["roleplay_session_id"] == session_id
    ]
    return max(orders, default=0) + 1


def next_turn_order(session_id: str) -> int:
    orders = [
        int(turn["turn_order"])
        for turn in sample_db.ROLEPLAY_TURNS
        if turn["roleplay_session_id"] == session_id
    ]
    return max(orders, default=0) + 1


def next_evaluation_order(session_id: str) -> int:
    orders = [
        int(item["evaluation_order"])
        for item in sample_db.ROLEPLAY_EVALUATIONS
        if item["roleplay_session_id"] == session_id
    ]
    return max(orders, default=0) + 1


def messages_for_session(session_id: str) -> list[dict[str, Any]]:
    return sorted(
        [
            message
            for message in sample_db.MESSAGES
            if message["roleplay_session_id"] == session_id
        ],
        key=lambda item: int(item["message_order"]),
    )


def build_initial_state(
    *,
    roleplay_session_id: str,
    learner_id: str,
    learner_input_text: str,
    input_method: str,
) -> dict[str, Any]:
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
        "judge_result": None,
        "rule_decision": None,
        "response_pack": None,
        "response_validation_result": None,
        "persistence_result": None,
        "final_feedback_result": None,
        "created_turn_id": None,
        "created_message_ids": [],
        "created_evaluation_id": None,
        "_node_logs": [],
    }


def set_node_output(state: dict[str, Any], output: dict[str, Any]) -> None:
    state["_sample_last_node_output"] = json_safe(output)


def public_state_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    return {
        key: json_safe(value)
        for key, value in state.items()
        if not key.startswith("_")
    }


def state_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(before) | set(after))
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in keys
        if before.get(key) != after.get(key)
    }


def timed_node(name: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def wrapper(state: dict[str, Any]) -> dict[str, Any]:
        before = public_state_snapshot(state)
        started = time.perf_counter()
        error = None
        try:
            result = fn(state)
        except Exception as exc:
            result = state
            error = {"type": type(exc).__name__, "message": str(exc)}
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        node_output = result.pop("_sample_last_node_output", {})
        after = public_state_snapshot(result)
        result.setdefault("_node_logs", []).append(
            {
                "node": name,
                "elapsed_ms": elapsed_ms,
                "node_output": node_output,
                "state_update": state_diff(before, after),
                "error": error,
            }
        )
        if error:
            raise RuntimeError(f"{name} failed: {error['message']}")
        return result

    return wrapper


def context_builder_node(state: dict[str, Any]) -> dict[str, Any]:
    session = find_one(sample_db.ROLEPLAY_SESSIONS, "roleplay_session_id", state["roleplay_session_id"])
    if session["learner_id"] != state["learner_id"]:
        raise ValueError("Learner does not own this roleplay session.")
    if session["end_status"] != "in_progress":
        raise ValueError("Roleplay session is not in progress.")

    current_step = find_one(sample_db.STEPS, "step_id", session["current_step_id"])
    scenario_version = find_one(sample_db.SCENARIO_VERSIONS, "scenario_version_id", session["scenario_version_id"])
    scenario = find_one(sample_db.SCENARIOS, "scenario_id", scenario_version["scenario_id"])
    scenario_character = find_scenario_character(current_step, scenario_version)
    scenario_location = find_scenario_location(current_step, scenario_version)
    roleplay_character = find_one(
        sample_db.ROLEPLAY_CHARACTERS,
        "roleplay_character_id",
        scenario_character["roleplay_character_id"],
    )
    roleplay_location = find_one(
        sample_db.ROLEPLAY_LOCATIONS,
        "roleplay_location_id",
        scenario_location["roleplay_location_id"],
    )
    recent_messages = messages_for_session(state["roleplay_session_id"])[-8:]
    sample_answers = [
        item["sample_answer_text"]
        for item in sorted(sample_db.STEP_SAMPLE_ANSWERS, key=lambda row: int(row["display_order"]))
        if item["step_id"] == current_step["step_id"]
        and item.get("language_code") == scenario_version.get("learning_language")
    ]

    state["session"] = serialize_session(session)
    state["scenario_version"] = serialize_scenario_version(scenario_version)
    state["scenario"] = serialize_scenario(scenario)
    state["current_step"] = serialize_step(current_step)
    state["character"] = serialize_character(scenario_character, roleplay_character)
    state["location"] = serialize_location(scenario_location, roleplay_location)
    state["recent_messages"] = [serialize_message(message) for message in recent_messages]
    state["step_sample_answers"] = sample_answers
    state["last_character_message_text"] = extract_last_message(state["recent_messages"], "roleplay_character")
    state["last_learner_message_text"] = extract_last_message(state["recent_messages"], "learner")

    set_node_output(
        state,
        {
            "session": state["session"],
            "scenario_version": state["scenario_version"],
            "scenario": state["scenario"],
            "current_step": state["current_step"],
            "character": state["character"],
            "location": state["location"],
            "recent_messages": state["recent_messages"],
            "step_sample_answers": state["step_sample_answers"],
            "last_character_message_text": state["last_character_message_text"],
            "last_learner_message_text": state["last_learner_message_text"],
        },
    )
    return state


def find_scenario_character(current_step: dict[str, Any], scenario_version: dict[str, Any]) -> dict[str, Any]:
    target_id = current_step.get("primary_scenario_roleplay_character_id")
    candidates = [
        item
        for item in sample_db.SCENARIO_ROLEPLAY_CHARACTERS
        if item["scenario_version_id"] == scenario_version["scenario_version_id"]
    ]
    if target_id:
        return find_one(candidates, "scenario_roleplay_character_id", target_id)
    return sorted(candidates, key=lambda item: (not item.get("is_primary"), int(item["display_order"])))[0]


def find_scenario_location(current_step: dict[str, Any], scenario_version: dict[str, Any]) -> dict[str, Any]:
    target_id = current_step.get("primary_scenario_location_id")
    candidates = [
        item
        for item in sample_db.SCENARIO_LOCATIONS
        if item["scenario_version_id"] == scenario_version["scenario_version_id"]
    ]
    if target_id:
        return find_one(candidates, "scenario_location_id", target_id)
    return sorted(candidates, key=lambda item: (not item.get("is_primary"), int(item["display_order"])))[0]


def serialize_session(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "roleplay_session_id": session["roleplay_session_id"],
        "learner_id": session["learner_id"],
        "scenario_version_id": session["scenario_version_id"],
        "current_step_id": session.get("current_step_id"),
        "total_chances": session["total_chances"],
        "remaining_chances": session["remaining_chances"],
        "end_status": session["end_status"],
        "current_step_fail_count": session["current_step_fail_count"],
    }


def serialize_scenario_version(version: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_version_id": version["scenario_version_id"],
        "scenario_id": version["scenario_id"],
        "version_number": version["version_number"],
        "learning_language": version["learning_language"],
        "default_system_language": version["default_system_language"],
        "default_total_chances": version["default_total_chances"],
        "status": version["status"],
    }


def serialize_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_id": scenario["scenario_id"],
        "title": scenario["title"],
        "description": scenario["description"],
        "difficulty": scenario["difficulty"],
    }


def serialize_step(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_id": step["step_id"],
        "scenario_version_id": step["scenario_version_id"],
        "step_order": step["step_order"],
        "step_title": step["step_title"],
        "step_goal": step["step_goal"],
        "initial_scene_text": step.get("initial_scene_text"),
        "initial_roleplay_character_action_text": step.get("initial_roleplay_character_action_text"),
        "initial_roleplay_character_dialogue_text": step.get("initial_roleplay_character_dialogue_text"),
        "initial_roleplay_character_dialogue_language": step.get("initial_roleplay_character_dialogue_language"),
        "initial_roleplay_character_dialogue_translation_json": parse_json_maybe(
            step.get("initial_roleplay_character_dialogue_translation_json")
        ),
        "roleplay_guidance_text": step.get("roleplay_guidance_text"),
        "primary_scenario_roleplay_character_id": step.get("primary_scenario_roleplay_character_id"),
        "primary_scenario_location_id": step.get("primary_scenario_location_id"),
    }


def serialize_character(scenario_character: dict[str, Any], character: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_roleplay_character_id": scenario_character["scenario_roleplay_character_id"],
        "roleplay_character_id": character["roleplay_character_id"],
        "role_name": scenario_character["scenario_role_name"],
        "name": character["name"],
        "description": character["description"],
        "persona_prompt": character.get("persona_prompt"),
    }


def serialize_location(scenario_location: dict[str, Any], location: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_location_id": scenario_location["scenario_location_id"],
        "roleplay_location_id": location["roleplay_location_id"],
        "name": location["name"],
        "description": location["description"],
        "location_prompt": location.get("location_prompt"),
    }


def serialize_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": message["message_id"],
        "roleplay_session_id": message["roleplay_session_id"],
        "roleplay_turn_id": message.get("roleplay_turn_id"),
        "step_id": message.get("step_id"),
        "scenario_roleplay_character_id": message.get("scenario_roleplay_character_id"),
        "message_order": message["message_order"],
        "sender_type": message["sender_type"],
        "generated_by": message.get("generated_by"),
        "message_type": message["message_type"],
        "text_content": message["text_content"],
        "text_language": message["text_language"],
        "translation_json": parse_json_maybe(message.get("translation_json")),
        "hint_level": message.get("hint_level"),
    }


def extract_last_message(messages: list[dict[str, Any]], sender_type: str) -> str | None:
    for message in reversed(messages):
        if message.get("sender_type") == sender_type:
            return message.get("text_content")
    return None


def judge_node(state: dict[str, Any]) -> dict[str, Any]:
    prompt = build_judge_prompt(state)
    raw_response = None
    used_fallback = True
    if state.get("_sample_config", {}).get("use_gemini"):
        raw_response = generate_gemini_json(JUDGE_SYSTEM_INSTRUCTION, prompt)
        if raw_response:
            try:
                state["judge_result"] = normalize_judge_result(parse_json_response(raw_response))
                used_fallback = False
            except Exception:
                state["judge_result"] = heuristic_judge_result(state)
        else:
            state["judge_result"] = heuristic_judge_result(state)
    else:
        state["judge_result"] = heuristic_judge_result(state)

    set_node_output(
        state,
        {
            "judge_result": state["judge_result"],
            "used_fallback": used_fallback,
            "raw_response_preview": (raw_response or "")[:1200],
        },
    )
    return state


def build_judge_prompt(state: dict[str, Any]) -> str:
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
        "judge_rules": [
            "Evaluate intent before grammar.",
            "pass means the step goal is clearly achieved with no major expression issue.",
            "soft_pass means the step goal is achieved but expression improvement is needed.",
            "fail means the step goal is not achieved, unclear, or off-topic.",
            "Do not mark a cultural issue unless the learner input clearly contains one.",
        ],
    }
    return compact_json(prompt_payload)


def generate_gemini_json(system_instruction: str, prompt: str) -> str | None:
    key = api_key()
    if not key or genai is None or types is None:
        return None
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=gemini_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
            ),
        )
        return response.text or ""
    except Exception as exc:
        st.session_state["last_provider_error"] = str(exc)
        return None


def parse_json_response(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    return json.loads(cleaned)


def normalize_judge_result(result: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "evaluation_result": result.get("evaluation_result"),
        "confidence": max(0.0, min(1.0, float(result.get("confidence", 0.0)))),
        "inferred_intent_text": str(result.get("inferred_intent_text") or ""),
        "step_goal_matched": bool(result.get("step_goal_matched")),
        "communication_success": bool(result.get("communication_success")),
        "issue_tags": list(result.get("issue_tags") or []),
        "correction_needed": bool(result.get("correction_needed")),
        "cultural_issue_detected": bool(result.get("cultural_issue_detected")),
        "evaluation_reason_text": str(result.get("evaluation_reason_text") or ""),
    }
    if normalized["evaluation_result"] == "pass":
        normalized["step_goal_matched"] = True
        normalized["communication_success"] = True
        normalized["correction_needed"] = False
    elif normalized["evaluation_result"] == "soft_pass":
        normalized["step_goal_matched"] = True
        normalized["communication_success"] = True
        normalized["correction_needed"] = True
    elif normalized["evaluation_result"] == "fail":
        normalized["step_goal_matched"] = False
        normalized["correction_needed"] = False
    else:
        raise ValueError("Judge Node returned an invalid evaluation_result.")
    return normalized


def heuristic_judge_result(state: dict[str, Any]) -> dict[str, Any]:
    text = normalize_text(state["learner_input_text"])
    order = int(state["current_step"].get("step_order") or 0)
    keyword_sets = {
        1: ["안녕", "지우개", "빌려"],
        2: ["저", "이름", "예요", "이에요"],
        3: ["필리핀", "사람", "나라", "에서"],
        4: ["학생", "회사원", "직업", "이에요", "예요"],
        5: ["반가", "안녕", "잘", "또", "만나"],
    }
    matched = [keyword for keyword in keyword_sets.get(order, []) if keyword in text]
    sample_match = any(normalize_text(sample) == text for sample in state.get("step_sample_answers", []))
    if sample_match or len(matched) >= min(2, len(keyword_sets.get(order, []))):
        evaluation = "pass" if sample_match or text.endswith(("요", "다")) else "soft_pass"
        return normalize_judge_result(
            {
                "evaluation_result": evaluation,
                "confidence": 0.72 if evaluation == "pass" else 0.62,
                "inferred_intent_text": "The learner appears to answer the current step goal.",
                "step_goal_matched": True,
                "communication_success": True,
                "issue_tags": [] if evaluation == "pass" else ["naturalness"],
                "correction_needed": evaluation == "soft_pass",
                "cultural_issue_detected": False,
                "evaluation_reason_text": "Local fallback matched the learner input to this step's expected intent.",
            }
        )
    return normalize_judge_result(
        {
            "evaluation_result": "fail",
            "confidence": 0.58,
            "inferred_intent_text": "The learner input does not clearly satisfy the current step.",
            "step_goal_matched": False,
            "communication_success": False,
            "issue_tags": ["clarity"],
            "correction_needed": False,
            "cultural_issue_detected": False,
            "evaluation_reason_text": "Local fallback could not match the expected intent for the current step.",
        }
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").casefold()


def game_rule_engine_node(state: dict[str, Any]) -> dict[str, Any]:
    judge_result = state["judge_result"]
    session_state = state["session"]
    current_step = state["current_step"]
    evaluation_result = judge_result["evaluation_result"]
    current_step_id = str(current_step["step_id"])
    remaining_before = int(session_state.get("remaining_chances") or 0)
    fail_before = int(session_state.get("current_step_fail_count") or 0)

    should_decrease = evaluation_result == "fail"
    remaining_after = max(0, remaining_before - 1) if should_decrease else remaining_before
    fail_after = fail_before + 1 if should_decrease else 0
    hint_level = decide_hint_level(fail_after) if should_decrease else "none"
    can_progress = evaluation_result in {"pass", "soft_pass"}
    next_step = (
        find_next_step(
            str(current_step["scenario_version_id"]),
            int(current_step["step_order"]),
        )
        if can_progress
        else None
    )
    rule_decision = build_rule_decision(
        evaluation_result=evaluation_result,
        current_step_id=current_step_id,
        next_step_id=next_step["step_id"] if next_step else None,
        remaining_chances_before=remaining_before,
        remaining_chances_after=remaining_after,
        fail_count_before=fail_before,
        fail_count_after=fail_after,
        hint_level=hint_level,
    )
    state["rule_decision"] = rule_decision
    set_node_output(state, {"rule_decision": rule_decision})
    return state


def build_rule_decision(
    *,
    evaluation_result: str,
    current_step_id: str,
    next_step_id: str | None,
    remaining_chances_before: int,
    remaining_chances_after: int,
    fail_count_before: int,
    fail_count_after: int,
    hint_level: str,
) -> dict[str, Any]:
    if evaluation_result == "fail":
        if remaining_chances_after <= 0:
            return {
                "evaluation_result": evaluation_result,
                "progress_outcome": "fail_session",
                "current_step_id": current_step_id,
                "next_step_id": None,
                "should_advance_step": False,
                "should_decrease_chance": True,
                "should_end_session": True,
                "remaining_chances_before": remaining_chances_before,
                "remaining_chances_after": remaining_chances_after,
                "current_step_fail_count_before": fail_count_before,
                "current_step_fail_count_after": fail_count_after,
                "end_status_after": "failed",
                "hint_level": hint_level,
                "transition_reason": "현재 단계 목표를 달성하지 못했고 남은 기회가 없어 세션을 실패 종료한다.",
            }
        return {
            "evaluation_result": evaluation_result,
            "progress_outcome": "stay_current_step",
            "current_step_id": current_step_id,
            "next_step_id": None,
            "should_advance_step": False,
            "should_decrease_chance": True,
            "should_end_session": False,
            "remaining_chances_before": remaining_chances_before,
            "remaining_chances_after": remaining_chances_after,
            "current_step_fail_count_before": fail_count_before,
            "current_step_fail_count_after": fail_count_after,
            "end_status_after": "in_progress",
            "hint_level": hint_level,
            "transition_reason": "현재 단계 목표를 달성하지 못했으므로 현재 단계를 유지하고 기회를 1 차감한다.",
        }
    if next_step_id:
        return {
            "evaluation_result": evaluation_result,
            "progress_outcome": "advance_to_next_step",
            "current_step_id": current_step_id,
            "next_step_id": next_step_id,
            "should_advance_step": True,
            "should_decrease_chance": False,
            "should_end_session": False,
            "remaining_chances_before": remaining_chances_before,
            "remaining_chances_after": remaining_chances_after,
            "current_step_fail_count_before": fail_count_before,
            "current_step_fail_count_after": 0,
            "end_status_after": "in_progress",
            "hint_level": "none",
            "transition_reason": "현재 단계 목표를 달성했으므로 다음 단계로 이동한다.",
        }
    return {
        "evaluation_result": evaluation_result,
        "progress_outcome": "complete_session",
        "current_step_id": current_step_id,
        "next_step_id": None,
        "should_advance_step": False,
        "should_decrease_chance": False,
        "should_end_session": True,
        "remaining_chances_before": remaining_chances_before,
        "remaining_chances_after": remaining_chances_after,
        "current_step_fail_count_before": fail_count_before,
        "current_step_fail_count_after": 0,
        "end_status_after": "completed",
        "hint_level": "none",
        "transition_reason": "마지막 단계의 목표를 달성했으므로 세션을 완료한다.",
    }


def decide_hint_level(current_step_fail_count_after: int) -> str:
    if current_step_fail_count_after <= 1:
        return "light"
    if current_step_fail_count_after == 2:
        return "medium"
    return "strong"


def response_pack_node(state: dict[str, Any]) -> dict[str, Any]:
    rule_decision = state["rule_decision"]
    state["next_step"] = (
        serialize_step(find_one(sample_db.STEPS, "step_id", rule_decision["next_step_id"]))
        if rule_decision.get("next_step_id")
        else None
    )
    prompt = build_response_pack_prompt(state)
    raw_response = None
    used_fallback = True
    response_pack = {"message_drafts": [], "correction_items": []}
    if state.get("_sample_config", {}).get("use_gemini"):
        raw_response = generate_gemini_json(RESPONSE_PACK_SYSTEM_INSTRUCTION, prompt)
        if raw_response:
            try:
                response_pack = parse_response_pack_response(raw_response)
                used_fallback = False
            except Exception:
                response_pack = {"message_drafts": [], "correction_items": []}
    response_pack = ensure_minimum_response_pack(state, response_pack)
    state["response_pack"] = response_pack
    set_node_output(
        state,
        {
            "next_step": state.get("next_step"),
            "response_pack": response_pack,
            "used_fallback": used_fallback,
            "raw_response_preview": (raw_response or "")[:1200],
        },
    )
    return state


def build_response_pack_prompt(state: dict[str, Any]) -> str:
    rule_decision = state["rule_decision"]
    prompt_payload = {
        "roleplay_session_id": state["roleplay_session_id"],
        "learner_id": state["learner_id"],
        "languages": {
            "learning_language": state["scenario_version"].get("learning_language"),
            "system_language": state["scenario_version"].get("default_system_language"),
            "rules": {
                "roleplay_character_dialogue_text": "learning_language",
                "scene_text": "system_language",
                "roleplay_character_action_text": "system_language",
                "hint": "system_language",
                "correction_feedback": "system_language",
            },
        },
        "scenario": state["scenario"],
        "current_step": state["current_step"],
        "next_step": state.get("next_step"),
        "character": state["character"],
        "role_contract": {
            "learner": "The learner/user is the person practicing the target role for the current scenario.",
            "roleplay_character": "The AI-generated roleplay_character is only the assigned character in this scenario.",
            "rule": "Never swap, merge, or imitate these roles.",
        },
        "location": state["location"],
        "recent_messages": state.get("recent_messages", []),
        "learner_input_text": state["learner_input_text"],
        "judge_result": state["judge_result"],
        "rule_decision": rule_decision,
        "generation_rules": generation_rules_for_state(state),
    }
    return compact_json(prompt_payload)


def generation_rules_for_state(state: dict[str, Any]) -> list[str]:
    rule_decision = state["rule_decision"]
    judge_result = state["judge_result"]
    rules = [
        "message_type values must use snake_case DB enum values.",
        "hint_level may appear only on hint messages.",
        "Never confuse the learner/user role with the roleplay_character role.",
        "roleplay_character_dialogue_text must be from the assigned character's perspective.",
    ]
    if rule_decision["progress_outcome"] in {"stay_current_step", "fail_session"}:
        rules.extend(
            [
                "Generate a hint message because the learner failed and stays or ends.",
                f"The hint message hint_level must be {rule_decision['hint_level']}.",
                "Use current_step.step_id for every generated message.",
            ]
        )
    elif rule_decision["progress_outcome"] == "advance_to_next_step":
        rules.extend(
            [
                "Do not generate a hint.",
                "Use next_step.step_id for next-step scene/action/dialogue messages.",
                "Generate short character dialogue that naturally enters the next step.",
            ]
        )
    elif rule_decision["progress_outcome"] == "complete_session":
        rules.extend(["Do not generate a hint.", "Generate only a concise completion response."])
    if judge_result and judge_result["evaluation_result"] == "soft_pass" and judge_result["correction_needed"]:
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


def parse_response_pack_response(raw_text: str) -> dict[str, Any]:
    parsed = parse_json_response(raw_text)
    drafts = parsed.get("message_drafts") or []
    corrections = parsed.get("correction_items") or []
    if not isinstance(drafts, list) or not isinstance(corrections, list):
        raise ValueError("Response Pack Node returned an invalid response_pack.")
    return {"message_drafts": drafts, "correction_items": corrections}


def ensure_minimum_response_pack(state: dict[str, Any], response_pack: dict[str, Any]) -> dict[str, Any]:
    drafts = list(response_pack.get("message_drafts") or [])
    corrections = list(response_pack.get("correction_items") or [])
    rule_decision = state["rule_decision"]
    judge_result = state["judge_result"]
    has_dialogue = any(draft.get("message_type") == "roleplay_character_dialogue_text" for draft in drafts)
    has_hint = any(draft.get("message_type") == "hint" for draft in drafts)
    has_correction_feedback = any(draft.get("message_type") == "correction_feedback" for draft in drafts)

    if rule_decision["progress_outcome"] in {"stay_current_step", "fail_session"} and not has_hint:
        drafts.insert(0, fallback_hint_draft(state))
    if (
        judge_result
        and judge_result["evaluation_result"] == "soft_pass"
        and judge_result["correction_needed"]
        and not has_correction_feedback
    ):
        drafts.insert(0, fallback_correction_feedback_draft(state))
    if not has_dialogue:
        drafts.append(fallback_dialogue_draft(state))
    if (
        judge_result
        and judge_result["evaluation_result"] == "soft_pass"
        and judge_result["correction_needed"]
        and not corrections
    ):
        corrections.append(
            {
                "type": (judge_result["issue_tags"][0] if judge_result.get("issue_tags") else "naturalness"),
                "original_text": state.get("learner_input_text") or "",
                "corrected_text": fallback_corrected_text(state),
                "reason_text": "This sounds more natural and polite for the current roleplay step.",
            }
        )
    return {"message_drafts": drafts, "correction_items": corrections}


def fallback_hint_draft(state: dict[str, Any]) -> dict[str, Any]:
    level = state["rule_decision"].get("hint_level") or "light"
    text_by_level = {
        "light": "Try again. Think about the goal of this step.",
        "medium": "Try again. Include the key request or response needed in this situation.",
        "strong": "Try again using a polite expression that closely matches the step goal.",
    }
    return {
        "message_type": "hint",
        "text_content": text_by_level.get(level, text_by_level["light"]),
        "text_language": system_language(state),
        "translation_json": None,
        "step_id": state["current_step"].get("step_id"),
        "scenario_roleplay_character_id": None,
        "hint_level": level if level != "none" else "light",
    }


def fallback_correction_feedback_draft(state: dict[str, Any]) -> dict[str, Any]:
    corrected = fallback_corrected_text(state)
    return {
        "message_type": "correction_feedback",
        "text_content": f'Good job. A more natural way to say it is: "{corrected}"',
        "text_language": system_language(state),
        "translation_json": None,
        "step_id": state["current_step"].get("step_id"),
        "scenario_roleplay_character_id": None,
        "hint_level": None,
    }


def fallback_dialogue_draft(state: dict[str, Any]) -> dict[str, Any]:
    rule_decision = state["rule_decision"]
    step_id = target_step_id_for_dialogue(state)
    next_step = state.get("next_step") or {}
    authored_dialogue = next_step.get("initial_roleplay_character_dialogue_text")
    authored_translation = next_step.get("initial_roleplay_character_dialogue_translation_json")
    if rule_decision["progress_outcome"] == "advance_to_next_step" and authored_dialogue:
        translation = authored_translation.get(system_language(state)) if isinstance(authored_translation, dict) else None
        text = authored_dialogue
        translation_json = {system_language(state): translation} if translation else None
    elif rule_decision["progress_outcome"] == "advance_to_next_step":
        text = next_step_dialogue_for_order(int(next_step.get("step_order") or 0))
        translation_json = None
    elif rule_decision["progress_outcome"] == "complete_session":
        text = "좋아요. 역할극을 마쳤습니다."
        translation_json = {system_language(state): "Good. The roleplay is complete."}
    elif rule_decision["progress_outcome"] == "fail_session":
        text = "괜찮습니다. 여기서 마무리할게요."
        translation_json = {system_language(state): "It's okay. Let's wrap up here."}
    elif rule_decision["progress_outcome"] == "stay_current_step":
        text = "다시 한 번 말해 주세요."
        translation_json = {system_language(state): "Please say it one more time."}
    else:
        text = "좋아요. 계속해 볼게요."
        translation_json = {system_language(state): "Good. Let's continue."}
    return {
        "message_type": "roleplay_character_dialogue_text",
        "text_content": text,
        "text_language": learning_language(state),
        "translation_json": translation_json,
        "step_id": step_id,
        "scenario_roleplay_character_id": state["character"].get("scenario_roleplay_character_id"),
        "hint_level": None,
    }


def next_step_dialogue_for_order(step_order: int) -> str:
    return {
        2: "저는 유진이에요. 이름이 뭐예요?",
        3: "어느 나라 사람이에요?",
        4: "학생이에요?",
        5: "만나서 반가웠어요.",
    }.get(step_order, "좋아요. 계속해 볼게요.")


def fallback_corrected_text(state: dict[str, Any]) -> str:
    samples = state.get("step_sample_answers") or []
    return samples[0] if samples else state.get("learner_input_text") or ""


def target_step_id_for_dialogue(state: dict[str, Any]) -> str | None:
    rule_decision = state["rule_decision"]
    if rule_decision["progress_outcome"] == "advance_to_next_step" and rule_decision.get("next_step_id"):
        return rule_decision["next_step_id"]
    return state["current_step"].get("step_id")


def learning_language(state: dict[str, Any]) -> str:
    return state["scenario_version"].get("learning_language") or "ko"


def system_language(state: dict[str, Any]) -> str:
    return state["scenario_version"].get("default_system_language") or "en"


def response_validator_node(state: dict[str, Any]) -> dict[str, Any]:
    response_pack = state.get("response_pack") or {"message_drafts": [], "correction_items": []}
    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(validate_required_dialogue(response_pack))
    errors.extend(validate_languages(state, response_pack))
    errors.extend(validate_hint_rules(state, response_pack))
    errors.extend(validate_correction_rules(state, response_pack))
    errors.extend(validate_step_ids(state, response_pack))
    warnings.extend(validate_lengths(response_pack))
    warnings.extend(validate_role_confusion_risk(state, response_pack))
    fallback_used = bool(errors)
    fallback_errors: list[str] = []
    if fallback_used:
        response_pack = ensure_minimum_response_pack(state, {"message_drafts": [], "correction_items": []})
        fallback_errors.extend(validate_required_dialogue(response_pack))
        fallback_errors.extend(validate_languages(state, response_pack))
        fallback_errors.extend(validate_hint_rules(state, response_pack))
        fallback_errors.extend(validate_correction_rules(state, response_pack))
        fallback_errors.extend(validate_step_ids(state, response_pack))
        if fallback_errors:
            errors.extend([f"fallback_error: {error}" for error in fallback_errors])
    validation_result = {
        "is_valid": not fallback_errors,
        "errors": errors,
        "warnings": warnings,
        "fallback_used": fallback_used,
    }
    state["response_pack"] = response_pack
    state["response_validation_result"] = validation_result
    set_node_output(
        state,
        {
            "response_validation_result": validation_result,
            "response_pack": response_pack,
        },
    )
    return state


def validate_required_dialogue(response_pack: dict[str, Any]) -> list[str]:
    if any(draft.get("message_type") == "roleplay_character_dialogue_text" for draft in response_pack.get("message_drafts", [])):
        return []
    return ["roleplay_character_dialogue_text is required."]


def validate_languages(state: dict[str, Any], response_pack: dict[str, Any]) -> list[str]:
    expected = {
        "scene_text": system_language(state),
        "roleplay_character_action_text": system_language(state),
        "roleplay_character_dialogue_text": learning_language(state),
        "hint": system_language(state),
        "correction_feedback": system_language(state),
    }
    errors = []
    for index, draft in enumerate(response_pack.get("message_drafts", [])):
        expected_language = expected[draft.get("message_type")]
        if draft.get("text_language") != expected_language:
            errors.append(
                f"message_drafts[{index}].text_language must be {expected_language} for {draft.get('message_type')}."
            )
    return errors


def validate_hint_rules(state: dict[str, Any], response_pack: dict[str, Any]) -> list[str]:
    rule_decision = state["rule_decision"]
    judge_result = state["judge_result"]
    should_generate_hint = bool(
        rule_decision
        and judge_result
        and rule_decision["progress_outcome"] in {"stay_current_step", "fail_session"}
        and judge_result["evaluation_result"] == "fail"
    )
    errors = []
    hint_drafts = [draft for draft in response_pack.get("message_drafts", []) if draft.get("message_type") == "hint"]
    if should_generate_hint and not hint_drafts:
        errors.append("hint is required for failed stay/fail_session outcomes.")
    if not should_generate_hint and hint_drafts:
        errors.append("hint must not be generated for this outcome.")
    for index, draft in enumerate(response_pack.get("message_drafts", [])):
        if draft.get("message_type") != "hint" and draft.get("hint_level") is not None:
            errors.append(f"message_drafts[{index}].hint_level is only allowed on hint messages.")
        if draft.get("message_type") == "hint":
            if draft.get("hint_level") is None:
                errors.append(f"message_drafts[{index}].hint_level is required.")
            elif draft.get("hint_level") != rule_decision["hint_level"]:
                errors.append(f"message_drafts[{index}].hint_level must match rule_decision.hint_level.")
    return errors


def validate_correction_rules(state: dict[str, Any], response_pack: dict[str, Any]) -> list[str]:
    judge_result = state["judge_result"]
    should_generate = bool(
        judge_result
        and judge_result["evaluation_result"] == "soft_pass"
        and judge_result["correction_needed"]
    )
    has_feedback = any(draft.get("message_type") == "correction_feedback" for draft in response_pack.get("message_drafts", []))
    errors = []
    if should_generate:
        if not response_pack.get("correction_items"):
            errors.append("correction_items are required for soft_pass correction.")
        if not has_feedback:
            errors.append("correction_feedback is required for soft_pass correction.")
    else:
        if response_pack.get("correction_items"):
            errors.append("correction_items must not be generated for this outcome.")
        if has_feedback:
            errors.append("correction_feedback must not be generated for this outcome.")
    return errors


def validate_step_ids(state: dict[str, Any], response_pack: dict[str, Any]) -> list[str]:
    allowed = {state["current_step"].get("step_id")}
    if state["rule_decision"].get("next_step_id"):
        allowed.add(state["rule_decision"]["next_step_id"])
    errors = []
    for index, draft in enumerate(response_pack.get("message_drafts", [])):
        if draft.get("step_id") not in allowed:
            errors.append(f"message_drafts[{index}].step_id must be current_step_id or next_step_id.")
    return errors


def validate_lengths(response_pack: dict[str, Any]) -> list[str]:
    return [
        f"message_drafts[{index}].text_content is long."
        for index, draft in enumerate(response_pack.get("message_drafts", []))
        if len(draft.get("text_content") or "") > 500
    ]


def validate_role_confusion_risk(state: dict[str, Any], response_pack: dict[str, Any]) -> list[str]:
    learner_texts = [state.get("learner_input_text") or "", *(state.get("step_sample_answers") or [])]
    normalized_learner_texts = {normalize_text(text) for text in learner_texts if normalize_text(text)}
    warnings = []
    for index, draft in enumerate(response_pack.get("message_drafts", [])):
        if draft.get("message_type") != "roleplay_character_dialogue_text":
            continue
        if normalize_text(draft.get("text_content") or "") in normalized_learner_texts:
            warnings.append(f"message_drafts[{index}].text_content may repeat learner-role text.")
    return warnings


def domain_persistence_node(state: dict[str, Any]) -> dict[str, Any]:
    rule_decision = state["rule_decision"]
    judge_result = state["judge_result"]
    response_pack = state["response_pack"]
    session = find_one(sample_db.ROLEPLAY_SESSIONS, "roleplay_session_id", state["roleplay_session_id"])
    now = now_iso()
    current_step_id = state["current_step"]["step_id"]
    turn_id = str(uuid4())
    sample_db.ROLEPLAY_TURNS.append(
        {
            "roleplay_turn_id": turn_id,
            "roleplay_session_id": state["roleplay_session_id"],
            "step_id": current_step_id,
            "next_step_id": rule_decision.get("next_step_id"),
            "turn_order": next_turn_order(state["roleplay_session_id"]),
            "input_method": state["input_method"],
            "remaining_chances_before": rule_decision["remaining_chances_before"],
            "remaining_chances_after": rule_decision["remaining_chances_after"],
            "end_status_after": rule_decision["end_status_after"],
            "created_at": now,
            "fail_count_before": rule_decision["current_step_fail_count_before"],
            "fail_count_after": rule_decision["current_step_fail_count_after"],
        }
    )
    created_messages = []
    message_order = next_message_order(state["roleplay_session_id"])
    learner_message = build_message(
        roleplay_session_id=state["roleplay_session_id"],
        roleplay_turn_id=turn_id,
        step_id=current_step_id,
        scenario_roleplay_character_id=None,
        message_order=message_order,
        sender_type="learner",
        generated_by=None,
        message_type="learner_input_text",
        text_content=state["learner_input_text"],
        text_language=learning_language(state),
        translation_json=None,
        hint_level=None,
    )
    sample_db.MESSAGES.append(learner_message)
    created_messages.append(learner_message)
    message_order += 1
    for draft in response_pack.get("message_drafts", []):
        message = message_from_draft(state, draft, turn_id, message_order)
        sample_db.MESSAGES.append(message)
        created_messages.append(message)
        message_order += 1
    evaluation_id = str(uuid4())
    sample_db.ROLEPLAY_EVALUATIONS.append(
        {
            "roleplay_evaluation_id": evaluation_id,
            "roleplay_turn_id": turn_id,
            "roleplay_session_id": state["roleplay_session_id"],
            "step_id": current_step_id,
            "evaluation_order": next_evaluation_order(state["roleplay_session_id"]),
            "learner_input_text": state["learner_input_text"],
            "evaluation_result": judge_result["evaluation_result"],
            "inferred_intent_text": judge_result["inferred_intent_text"],
            "step_goal_matched": judge_result["step_goal_matched"],
            "evaluation_reason_text": judge_result["evaluation_reason_text"],
            "correction_json": response_pack.get("correction_items") or None,
            "cultural_issue_detected": judge_result["cultural_issue_detected"],
            "should_advance_step": rule_decision["should_advance_step"],
            "should_decrease_chance": rule_decision["should_decrease_chance"],
            "should_end_session": rule_decision["should_end_session"],
            "created_at": now,
        }
    )
    if rule_decision["progress_outcome"] == "advance_to_next_step" and rule_decision.get("next_step_id"):
        session["current_step_id"] = rule_decision["next_step_id"]
    session["remaining_chances"] = rule_decision["remaining_chances_after"]
    session["current_step_fail_count"] = rule_decision["current_step_fail_count_after"]
    session["end_status"] = rule_decision["end_status_after"]
    session["ended_at"] = now if rule_decision["should_end_session"] else None
    session["updated_at"] = now

    session_after = {
        "roleplay_session_id": session["roleplay_session_id"],
        "current_step_id": session.get("current_step_id"),
        "remaining_chances": session["remaining_chances"],
        "end_status": session["end_status"],
        "current_step_fail_count": session["current_step_fail_count"],
        "ended_at": session.get("ended_at"),
    }
    persistence_result = {
        "created_turn_id": turn_id,
        "created_message_ids": [message["message_id"] for message in created_messages],
        "created_evaluation_id": evaluation_id,
        "session_after": session_after,
        "turn_messages": [serialize_message(message) for message in created_messages],
    }
    state["created_turn_id"] = turn_id
    state["created_message_ids"] = persistence_result["created_message_ids"]
    state["created_evaluation_id"] = evaluation_id
    state["persistence_result"] = persistence_result
    state["session"].update(session_after)
    set_node_output(state, {"persistence_result": persistence_result})
    return state


def build_message(
    *,
    roleplay_session_id: str,
    roleplay_turn_id: str | None,
    step_id: str | None,
    scenario_roleplay_character_id: str | None,
    message_order: int,
    sender_type: str,
    generated_by: str | None,
    message_type: str,
    text_content: str,
    text_language: str,
    translation_json: dict[str, Any] | None,
    hint_level: str | None,
) -> dict[str, Any]:
    return {
        "message_id": str(uuid4()),
        "roleplay_session_id": roleplay_session_id,
        "roleplay_turn_id": roleplay_turn_id,
        "step_id": step_id,
        "scenario_roleplay_character_id": scenario_roleplay_character_id,
        "message_order": message_order,
        "sender_type": sender_type,
        "generated_by": generated_by,
        "message_type": message_type,
        "text_content": text_content,
        "text_language": text_language,
        "translation_json": translation_json,
        "audio_file_id": None,
        "created_at": now_iso(),
        "hint_level": hint_level,
    }


def message_from_draft(state: dict[str, Any], draft: dict[str, Any], turn_id: str, message_order: int) -> dict[str, Any]:
    sender_type = sender_type_for_message_type(draft["message_type"])
    scenario_character_id = draft.get("scenario_roleplay_character_id")
    if sender_type == "roleplay_character" and not scenario_character_id:
        scenario_character_id = state["character"].get("scenario_roleplay_character_id")
    return build_message(
        roleplay_session_id=state["roleplay_session_id"],
        roleplay_turn_id=turn_id,
        step_id=draft.get("step_id"),
        scenario_roleplay_character_id=scenario_character_id,
        message_order=message_order,
        sender_type=sender_type,
        generated_by="ai_agent",
        message_type=draft["message_type"],
        text_content=draft["text_content"],
        text_language=draft["text_language"],
        translation_json=parse_json_maybe(draft.get("translation_json")),
        hint_level=draft.get("hint_level"),
    )


def sender_type_for_message_type(message_type: str) -> str:
    if message_type in {"scene_text", "hint", "correction_feedback"}:
        return "system"
    if message_type in {"roleplay_character_action_text", "roleplay_character_dialogue_text"}:
        return "roleplay_character"
    return "learner"


def build_graph_runner() -> Callable[[dict[str, Any]], dict[str, Any]]:
    node_functions = {
        "context_builder": timed_node("context_builder", context_builder_node),
        "judge": timed_node("judge", judge_node),
        "game_rule_engine": timed_node("game_rule_engine", game_rule_engine_node),
        "response_pack": timed_node("response_pack", response_pack_node),
        "response_validator": timed_node("response_validator", response_validator_node),
        "domain_persistence": timed_node("domain_persistence", domain_persistence_node),
    }
    if StateGraph is None:
        def sequential(state: dict[str, Any]) -> dict[str, Any]:
            for node_name in NODE_SEQUENCE:
                state = node_functions[node_name](state)
            return state
        return sequential

    graph = StateGraph(dict)
    for node_name in NODE_SEQUENCE:
        graph.add_node(node_name, node_functions[node_name])
    graph.add_edge(START, "context_builder")
    graph.add_edge("context_builder", "judge")
    graph.add_edge("judge", "game_rule_engine")
    graph.add_edge("game_rule_engine", "response_pack")
    graph.add_edge("response_pack", "response_validator")
    graph.add_edge("response_validator", "domain_persistence")
    graph.add_edge("domain_persistence", END)
    compiled = graph.compile()
    return compiled.invoke


def run_roleplay_turn(text: str, *, use_gemini: bool) -> dict[str, Any]:
    state = build_initial_state(
        roleplay_session_id=st.session_state["roleplay_session_id"],
        learner_id=LEARNER_ID,
        learner_input_text=text,
        input_method=INPUT_METHOD,
    )
    state["_sample_config"] = {"use_gemini": use_gemini}
    runner = build_graph_runner()
    return runner(state)


def current_session() -> dict[str, Any]:
    return find_one(sample_db.ROLEPLAY_SESSIONS, "roleplay_session_id", st.session_state["roleplay_session_id"])


def current_step_for_ui() -> dict[str, Any]:
    session = current_session()
    return find_one(sample_db.STEPS, "step_id", session["current_step_id"])


def render_chat_message(message: dict[str, Any]) -> None:
    message_type = message["message_type"]
    sender = message["sender_type"]
    if sender == "learner":
        with st.chat_message("user"):
            st.markdown(message["text_content"])
        return
    with st.chat_message("assistant"):
        if message_type == "scene_text":
            st.caption("Scene")
            st.markdown(message["text_content"])
        elif message_type == "roleplay_character_action_text":
            st.caption("Action")
            st.markdown(f"*{message['text_content']}*")
        elif message_type == "hint":
            st.caption(f"Hint: {message.get('hint_level') or ''}")
            st.info(message["text_content"])
        elif message_type == "correction_feedback":
            st.caption("Correction")
            st.warning(message["text_content"])
        else:
            st.caption("유진")
            st.markdown(message["text_content"])
            translation = parse_json_maybe(message.get("translation_json"))
            if isinstance(translation, dict) and translation.get("en"):
                st.caption(translation["en"])


def render_node_logs(logs: list[dict[str, Any]]) -> None:
    st.subheader("Node Trace")
    if not logs:
        st.caption("Send a message to see node timings, node output, and state updates.")
        return
    total_ms = round(sum(float(log["elapsed_ms"]) for log in logs), 2)
    st.caption(f"Total node time: {total_ms} ms")
    for index, log in enumerate(logs, start=1):
        title = f"{index}. {log['node']} - {log['elapsed_ms']} ms"
        with st.expander(title, expanded=index == len(logs)):
            if log.get("error"):
                st.error(log["error"])
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Node output**")
                st.json(log.get("node_output") or {})
            with col2:
                st.markdown("**State update**")
                st.json(log.get("state_update") or {})


def render_fake_db() -> None:
    with st.expander("Fake DB runtime variables", expanded=False):
        st.json(
            {
                "ROLEPLAY_SESSIONS": sample_db.ROLEPLAY_SESSIONS,
                "ROLEPLAY_TURNS": sample_db.ROLEPLAY_TURNS,
                "MESSAGES": messages_for_session(st.session_state["roleplay_session_id"]),
                "ROLEPLAY_EVALUATIONS": sample_db.ROLEPLAY_EVALUATIONS,
            }
        )


def main() -> None:
    st.set_page_config(page_title="Roleplaying Sample", page_icon=None, layout="wide")
    ensure_runtime_tables()
    if "roleplay_session_id" not in st.session_state:
        st.session_state["roleplay_session_id"] = reset_fake_db()
    if "last_node_logs" not in st.session_state:
        st.session_state["last_node_logs"] = []
    if "last_provider_error" not in st.session_state:
        st.session_state["last_provider_error"] = None

    session = current_session()
    step = current_step_for_ui()
    total_steps = len(sorted_steps())
    use_gemini_default = bool(api_key() and genai is not None)

    st.title("Roleplaying Sample")

    with st.sidebar:
        st.header("Session")
        if st.button("Reset sample session", use_container_width=True):
            st.session_state["roleplay_session_id"] = reset_fake_db()
            st.session_state["last_node_logs"] = []
            st.session_state["last_provider_error"] = None
            st.rerun()
        use_gemini = st.checkbox("Use Gemini nodes", value=use_gemini_default)
        st.caption(f"Model: {gemini_model()}")
        if use_gemini and not api_key():
            st.warning("No GEMINI_API_KEY or GOOGLE_API_KEY was found. Local fallback will be used.")
        if st.session_state.get("last_provider_error"):
            st.warning(f"Provider fallback: {st.session_state['last_provider_error']}")
        st.metric("Life", session["remaining_chances"])
        st.metric("Step", f"{step['step_order']} / {total_steps}")
        st.caption(f"Status: {session['end_status']}")
        st.caption(f"Current step: {step['step_title']}")
        samples = [
            item["sample_answer_text"]
            for item in sorted(sample_db.STEP_SAMPLE_ANSWERS, key=lambda row: int(row["display_order"]))
            if item["step_id"] == step["step_id"]
        ]
        if samples:
            st.markdown("Sample answers")
            for sample in samples:
                st.code(sample, language=None)

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Roleplay Chat")
        for message in messages_for_session(st.session_state["roleplay_session_id"]):
            render_chat_message(message)
        if session["end_status"] == "in_progress":
            learner_text = st.chat_input("Type your Korean reply")
            if learner_text:
                try:
                    final_state = run_roleplay_turn(learner_text, use_gemini=use_gemini)
                    st.session_state["last_node_logs"] = final_state.get("_node_logs", [])
                except Exception as exc:
                    st.error(str(exc))
                st.rerun()
        else:
            st.info(f"Session ended: {session['end_status']}. Reset to run again.")

    with right:
        render_node_logs(st.session_state["last_node_logs"])
        render_fake_db()


if __name__ == "__main__":
    main()
