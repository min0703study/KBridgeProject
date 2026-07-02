from __future__ import annotations

from uuid import uuid4

from backend.app.agents.roleplay.logging import log_node_event
from backend.app.core.config import get_settings
from backend.app.schemas.roleplay import (
    AssistantMessage,
    CorrectionFeedback,
    CurrentRoleplayStep,
    Evaluation,
    RoleplayCharacterSummary,
    RoleplayDevPerfectAnswerRequest,
    RoleplayIngameResponse,
    RoleplayIngameUiState,
    RoleplayLocationSummary,
    RoleplayScenarioSummary,
    RoleplaySessionCreateRequest,
    RoleplaySessionCreateResponse,
    RoleplaySessionStatus,
    RoleplayTextTurnRequest,
    RoleplayTurnMessage,
    RoleplayTurnResponse,
    RoleplayUiState,
    RoleplayVersionSummary,
    StepSampleAnswerSummary,
)
from backend.app.services.roleplay_voice_service import (
    MissingProviderKeyError,
    text_to_speech_base64,
)
from samples.agents.sample_roleplaying import sample_roleplaying_backend as sample_backend

sample_db = sample_backend.sample_db


class SampleRoleplayingAdapterError(ValueError):
    status_code = 400


class SampleRoleplayingNotFoundError(SampleRoleplayingAdapterError):
    status_code = 404


class SampleRoleplayingTurnError(SampleRoleplayingAdapterError):
    status_code = 422


class SampleRoleplayingProviderError(SampleRoleplayingAdapterError):
    status_code = 503


def create_sample_roleplay_session(
    payload: RoleplaySessionCreateRequest | None = None,
) -> RoleplaySessionCreateResponse:
    sample_backend.ensure_runtime_tables()
    payload = payload or RoleplaySessionCreateRequest()

    version = _scenario_version(payload.scenario_version_id)
    first_step = _first_step(version["scenario_version_id"])
    learner_id = payload.learner_id or sample_backend.LEARNER_ID

    # sample_backend.run_roleplay_turn uses this module-level learner id when
    # building the state, so keep the fake session owner aligned with it.
    sample_backend.LEARNER_ID = learner_id

    now = sample_backend.now_iso()
    session = {
        "roleplay_session_id": str(uuid4()),
        "learner_id": learner_id,
        "scenario_version_id": version["scenario_version_id"],
        "current_step_id": first_step["step_id"],
        "total_chances": version["default_total_chances"],
        "remaining_chances": version["default_total_chances"],
        "end_status": "in_progress",
        "started_at": now,
        "ended_at": None,
        "created_at": now,
        "updated_at": now,
        "current_step_fail_count": 0,
    }
    sample_db.ROLEPLAY_SESSIONS.append(session)
    sample_backend.add_initial_step_messages(session["roleplay_session_id"], first_step)
    sample_backend.warmup_sample_roleplay_runtime()

    return _session_create_response(session)


def get_sample_convenience_store_ingame() -> RoleplayIngameResponse:
    sample_backend.ensure_runtime_tables()
    version = sample_backend.first_scenario_version()
    first_step = _first_step(version["scenario_version_id"])
    return _ingame_response(version, first_step)


async def run_sample_roleplay_session_text_turn(
    roleplay_session_id: str,
    payload: RoleplayTextTurnRequest,
) -> RoleplayTurnResponse:
    text_content = (payload.text_content or "").strip()
    if not text_content:
        raise SampleRoleplayingTurnError("text_content is required.")
    return _run_sample_turn(
        roleplay_session_id,
        text_content,
        input_method="text",
        include_tts=True,
    )


async def run_sample_roleplay_session_dev_perfect_answer_turn(
    roleplay_session_id: str,
    payload: RoleplayDevPerfectAnswerRequest | None = None,
) -> RoleplayTurnResponse:
    del payload
    state = _build_context_state(roleplay_session_id)
    sample_answer = _dev_perfect_answer_text(state)
    return _run_sample_turn(
        roleplay_session_id,
        sample_answer,
        input_method="text",
        include_tts=False,
    )


async def run_sample_roleplay_session_turn(
    roleplay_session_id: str,
    audio_bytes: bytes,
    filename: str | None = None,
    client_turn_id: str | None = None,
) -> RoleplayTurnResponse:
    del filename, client_turn_id
    if not audio_bytes:
        raise SampleRoleplayingTurnError("audio_file is required.")
    try:
        transcript = sample_backend.transcribe_recorded_audio(audio_bytes)
    except Exception as exc:
        raise SampleRoleplayingTurnError(str(exc)) from exc
    if not transcript.strip():
        raise SampleRoleplayingTurnError("Speech transcript was empty.")
    return _run_sample_turn(
        roleplay_session_id,
        transcript.strip(),
        input_method="voice",
        include_tts=True,
    )


def _run_sample_turn(
    roleplay_session_id: str,
    text: str,
    *,
    input_method: str,
    include_tts: bool,
) -> RoleplayTurnResponse:
    _session(roleplay_session_id)
    try:
        final_state = sample_backend.run_roleplay_turn(
            text,
            roleplay_session_id=roleplay_session_id,
            use_llm=True,
            judge_model=sample_backend.default_judge_model(),
            response_model=sample_backend.default_response_model(),
            input_method=input_method,
        )
    except LookupError as exc:
        raise SampleRoleplayingNotFoundError(str(exc)) from exc
    except Exception as exc:
        raise SampleRoleplayingTurnError(str(exc)) from exc

    _log_node_trace_if_enabled(final_state)
    return _turn_response(final_state, text, include_tts=include_tts)


def _build_context_state(roleplay_session_id: str) -> dict:
    state = sample_backend.build_initial_state(
        roleplay_session_id=roleplay_session_id,
        learner_id=sample_backend.LEARNER_ID,
        learner_input_text="",
        input_method="text",
    )
    try:
        return sample_backend.context_builder_node(state)
    except LookupError as exc:
        raise SampleRoleplayingNotFoundError(str(exc)) from exc
    except Exception as exc:
        raise SampleRoleplayingTurnError(str(exc)) from exc


def _turn_response(
    final_state: dict,
    transcript: str,
    *,
    include_tts: bool,
) -> RoleplayTurnResponse:
    response_pack = final_state.get("response_pack") or {}
    rule_decision = final_state.get("rule_decision") or {}
    judge_result = final_state.get("judge_result") or {}
    persistence = final_state.get("persistence_result") or {}
    session_after = persistence.get("session_after") or final_state.get("session") or {}
    display_step = _display_step(final_state)
    correction_items = response_pack.get("correction_items") or []
    correction_item = correction_items[0] if correction_items else None
    feedback = _feedback(correction_item) if correction_item else None
    assistant_text, assistant_translation = _assistant_dialogue(response_pack)
    audio_base64 = _assistant_audio_base64(assistant_text, include_tts=include_tts)
    end_status = session_after.get("end_status") or "in_progress"

    return RoleplayTurnResponse(
        transcript=transcript,
        assistant_message=AssistantMessage(
            ko=assistant_text,
            en=assistant_translation,
            audio_base64=audio_base64,
        ),
        evaluation=Evaluation(
            result=judge_result.get("evaluation_result") or "soft_pass",
            issue_tags=[
                tag
                for tag in judge_result.get("issue_tags", [])
                if tag
                in {
                    "grammar",
                    "vocabulary",
                    "politeness",
                    "naturalness",
                    "culturalContext",
                    "taskExpression",
                    "clarity",
                    "offTopic",
                }
            ],
            correction_needed=bool(judge_result.get("correction_needed")),
        ),
        feedback=feedback,
        ui_state=RoleplayUiState(
            remaining_chances=int(session_after.get("remaining_chances") or 0),
            score_count=0,
            current_step_label=_current_step_label(display_step),
            current_step_order=int(display_step.get("step_order") or 1),
            current_step_guidance_text=display_step.get("roleplay_guidance_text"),
            total_steps=_total_steps(display_step.get("scenario_version_id")),
            should_show_feedback=feedback is not None,
        ),
        turn_messages=[
            _turn_message(message)
            for message in persistence.get("turn_messages", [])
            if message.get("message_type")
            in {
                "scene_text",
                "roleplay_character_action_text",
                "roleplay_character_dialogue_text",
                "learner_input_text",
                "hint",
                "correction_feedback",
            }
        ],
        session_status=RoleplaySessionStatus(
            end_status=end_status,
            is_ended=end_status in {"completed", "failed", "abandoned"},
            current_step_id=session_after.get("current_step_id"),
            created_turn_id=persistence.get("created_turn_id"),
        ),
    )


def _assistant_audio_base64(assistant_text: str, *, include_tts: bool) -> str:
    if not include_tts or not assistant_text:
        return ""

    try:
        return text_to_speech_base64(assistant_text)
    except (MissingProviderKeyError, TypeError) as exc:
        raise SampleRoleplayingProviderError(str(exc)) from exc


def _log_node_trace_if_enabled(final_state: dict) -> None:
    if not _node_trace_log_enabled():
        return

    node_logs = final_state.get("_node_logs") or []
    if not node_logs:
        return

    persistence = final_state.get("persistence_result") or {}
    session_after = persistence.get("session_after") or final_state.get("session") or {}
    log_node_event(
        "sample_node_trace",
        "sample_roleplaying",
        {
            "roleplay_session_id": final_state.get("roleplay_session_id"),
            "created_turn_id": persistence.get("created_turn_id"),
            "end_status": session_after.get("end_status"),
            "node_logs": node_logs,
        },
    )


def _node_trace_log_enabled() -> bool:
    return get_settings().roleplay_node_trace_log


def _assistant_dialogue(response_pack: dict) -> tuple[str, str]:
    for draft in response_pack.get("message_drafts", []):
        if draft.get("message_type") == "roleplay_character_dialogue_text":
            translation_json = sample_backend.parse_json_maybe(draft.get("translation_json"))
            return draft.get("text_content") or "", _translation_text(translation_json)
    return "", ""


def _feedback(correction_item: dict) -> CorrectionFeedback:
    corrected_text = correction_item.get("corrected_text") or ""
    reason_text = correction_item.get("reason_text") or "This sounds more natural for this situation."
    return CorrectionFeedback(
        previous_text=correction_item.get("original_text") or "",
        better_way=corrected_text,
        politeness_note=reason_text,
        grammar_note=reason_text,
    )


def _display_step(final_state: dict) -> dict:
    rule_decision = final_state.get("rule_decision") or {}
    next_step = final_state.get("next_step")
    if (
        rule_decision.get("progress_outcome") == "advance_to_next_step"
        and isinstance(next_step, dict)
        and next_step
    ):
        return next_step
    return final_state.get("current_step") or {}


def _turn_message(message: dict) -> RoleplayTurnMessage:
    return RoleplayTurnMessage(
        message_id=message.get("message_id"),
        sender_type=message["sender_type"],
        message_type=message["message_type"],
        text_content=message.get("text_content") or "",
        text_language=message.get("text_language") or "ko",
        translation_json=sample_backend.parse_json_maybe(message.get("translation_json")),
        step_id=message.get("step_id"),
        hint_level=message.get("hint_level"),
    )


def _ingame_response(version: dict, step: dict) -> RoleplayIngameResponse:
    scenario = _scenario(version["scenario_id"])
    scenario_location = _scenario_location(version["scenario_version_id"], step)
    roleplay_location = _roleplay_location(scenario_location["roleplay_location_id"])
    scenario_character = _scenario_character(version["scenario_version_id"], step)
    roleplay_character = _roleplay_character(scenario_character["roleplay_character_id"])

    return RoleplayIngameResponse(
        scenario=RoleplayScenarioSummary(
            scenario_id=scenario["scenario_id"],
            title=scenario["title"],
            description=scenario["description"],
            difficulty=scenario["difficulty"],
        ),
        version=RoleplayVersionSummary(
            scenario_version_id=version["scenario_version_id"],
            learning_language=version["learning_language"],
            default_system_language=version["default_system_language"],
            default_total_chances=version["default_total_chances"],
        ),
        location=RoleplayLocationSummary(
            scenario_location_id=scenario_location["scenario_location_id"],
            roleplay_location_id=roleplay_location["roleplay_location_id"],
            name=roleplay_location["name"],
            description=roleplay_location["description"],
            background_image_url="/roleplay_ingame_image/roleplay_university_student.png",
        ),
        character=RoleplayCharacterSummary(
            scenario_roleplay_character_id=scenario_character["scenario_roleplay_character_id"],
            roleplay_character_id=roleplay_character["roleplay_character_id"],
            role_name=scenario_character["scenario_role_name"],
            name=roleplay_character["name"],
            description=roleplay_character["description"],
            image_url=None,
        ),
        current_step=CurrentRoleplayStep(
            step_id=step["step_id"],
            step_order=int(step["step_order"]),
            step_title=step["step_title"],
            step_goal=step["step_goal"],
            guidance_text=step.get("roleplay_guidance_text"),
            scene_text=step.get("initial_scene_text"),
            character_action_text=step.get("initial_roleplay_character_action_text"),
            character_dialogue_text=step.get("initial_roleplay_character_dialogue_text"),
            character_dialogue_language=step.get("initial_roleplay_character_dialogue_language") or "ko",
            character_dialogue_translation_json=sample_backend.parse_json_maybe(
                step.get("initial_roleplay_character_dialogue_translation_json")
            ),
            sample_answers=[
                StepSampleAnswerSummary(
                    step_sample_answer_id=answer["step_sample_answer_id"],
                    text=answer["sample_answer_text"],
                    language_code=answer["language_code"],
                    display_order=int(answer["display_order"]),
                )
                for answer in _sample_answers(step["step_id"])
            ],
        ),
        ui_state=RoleplayIngameUiState(
            total_chances=int(version["default_total_chances"]),
            remaining_chances=int(version["default_total_chances"]),
            current_step_order=int(step["step_order"]),
            total_steps=_total_steps(version["scenario_version_id"]),
        ),
    )


def _session_create_response(session: dict) -> RoleplaySessionCreateResponse:
    return RoleplaySessionCreateResponse(
        roleplay_session_id=session["roleplay_session_id"],
        learner_id=session["learner_id"],
        scenario_version_id=session["scenario_version_id"],
        current_step_id=session["current_step_id"],
        total_chances=int(session["total_chances"]),
        remaining_chances=int(session["remaining_chances"]),
        end_status=session["end_status"],
        current_step_fail_count=int(session["current_step_fail_count"]),
    )


def _current_step_label(step: dict) -> str:
    return f"Step {int(step.get('step_order') or 1)}: {step.get('step_title') or ''}"


def _dev_perfect_answer_text(state: dict) -> str:
    sample_answers = state.get("step_sample_answers") or []
    if sample_answers:
        return str(sample_answers[0]).strip()
    step = state.get("current_step") or {}
    return str(step.get("roleplay_guidance_text") or step.get("step_goal") or "Okay.").strip()


def _translation_text(translation_json: object) -> str:
    if isinstance(translation_json, dict):
        return str(translation_json.get("en") or translation_json.get("EN") or "")
    return ""


def _scenario_version(scenario_version_id: str | None = None) -> dict:
    if scenario_version_id:
        return _find(sample_db.SCENARIO_VERSIONS, "scenario_version_id", scenario_version_id)
    return sample_backend.first_scenario_version()


def _first_step(scenario_version_id: str) -> dict:
    steps = [
        step
        for step in sample_backend.sorted_steps()
        if step["scenario_version_id"] == scenario_version_id
    ]
    if not steps:
        raise SampleRoleplayingNotFoundError("First step was not found.")
    return steps[0]


def _total_steps(scenario_version_id: str | None) -> int:
    if not scenario_version_id:
        return len(sample_backend.sorted_steps())
    return len(
        [
            step
            for step in sample_db.STEPS
            if step["scenario_version_id"] == scenario_version_id
        ]
    )


def _session(roleplay_session_id: str) -> dict:
    return _find(sample_db.ROLEPLAY_SESSIONS, "roleplay_session_id", roleplay_session_id)


def _scenario(scenario_id: str) -> dict:
    return _find(sample_db.SCENARIOS, "scenario_id", scenario_id)


def _scenario_location(scenario_version_id: str, step: dict) -> dict:
    target_id = step.get("primary_scenario_location_id")
    candidates = [
        item
        for item in sample_db.SCENARIO_LOCATIONS
        if item["scenario_version_id"] == scenario_version_id
    ]
    if target_id:
        return _find(candidates, "scenario_location_id", target_id)
    if not candidates:
        raise SampleRoleplayingNotFoundError("Roleplay scenario location was not found.")
    return sorted(candidates, key=lambda item: (not item.get("is_primary"), int(item["display_order"])))[0]


def _roleplay_location(roleplay_location_id: str) -> dict:
    return _find(sample_db.ROLEPLAY_LOCATIONS, "roleplay_location_id", roleplay_location_id)


def _scenario_character(scenario_version_id: str, step: dict) -> dict:
    target_id = step.get("primary_scenario_roleplay_character_id")
    candidates = [
        item
        for item in sample_db.SCENARIO_ROLEPLAY_CHARACTERS
        if item["scenario_version_id"] == scenario_version_id
    ]
    if target_id:
        return _find(candidates, "scenario_roleplay_character_id", target_id)
    if not candidates:
        raise SampleRoleplayingNotFoundError("Roleplay character was not found.")
    return sorted(candidates, key=lambda item: (not item.get("is_primary"), int(item["display_order"])))[0]


def _roleplay_character(roleplay_character_id: str) -> dict:
    return _find(sample_db.ROLEPLAY_CHARACTERS, "roleplay_character_id", roleplay_character_id)


def _sample_answers(step_id: str) -> list[dict]:
    return sorted(
        [
            answer
            for answer in sample_db.STEP_SAMPLE_ANSWERS
            if answer["step_id"] == step_id
        ],
        key=lambda answer: int(answer["display_order"]),
    )


def _find(table: list[dict], key: str, value: str) -> dict:
    for item in table:
        if str(item.get(key)) == str(value):
            return item
    raise SampleRoleplayingNotFoundError(f"{key}={value} was not found.")


__all__ = [
    "SampleRoleplayingAdapterError",
    "SampleRoleplayingNotFoundError",
    "SampleRoleplayingProviderError",
    "SampleRoleplayingTurnError",
    "create_sample_roleplay_session",
    "get_sample_convenience_store_ingame",
    "run_sample_roleplay_session_dev_perfect_answer_turn",
    "run_sample_roleplay_session_text_turn",
    "run_sample_roleplay_session_turn",
]
