from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import sys
import time
import wave
from collections.abc import Iterable
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Generic, Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, ValidationError

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - the UI shows a clear fallback state.
    genai = None
    types = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - OpenAI is optional for this sample.
    OpenAI = None

try:
    from elevenlabs.client import ElevenLabs
except Exception:  # pragma: no cover - TTS is optional for this sample.
    ElevenLabs = None

try:
    from google.cloud import speech
except Exception:  # pragma: no cover - STT is optional for this sample.
    speech = None

try:
    from kiwipiepy import Kiwi
except Exception:  # pragma: no cover - Kiwi is optional for this sample.
    Kiwi = None

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - sequential fallback keeps the sample usable.
    END = START = StateGraph = None

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[2]
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import sample_roleplaying_db2 as sample_db


LEARNER_ID = "23978a46-2c8e-4e2c-aa1d-4c37380b436e"
INPUT_METHOD = "text"
ELEVENLABS_MODEL = "eleven_flash_v2_5"
ELEVENLABS_VOICE_ID = "IKne3meq5aSn9XLyUdCD"
RESPONSE_PACK_MAX_OUTPUT_TOKENS = 1200
LLM_MODEL_OPTIONS = {
    "Gemini 3.1 Flash Lite": "gemini-3.1-flash-lite",
    "GPT-5.4 mini": "gpt-5.4-mini",
}
EvaluationResult = Literal["pass", "soft_pass", "fail"]
IssueTag = Literal[
    "grammar",
    "vocabulary",
    "politeness",
    "naturalness",
    "culturalContext",
    "taskExpression",
    "clarity",
    "offTopic",
]
MessageType = Literal[
    "scene_text",
    "roleplay_character_action_text",
    "roleplay_character_dialogue_text",
    "hint",
    "correction_feedback",
]
StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)
NODE_SEQUENCE = [
    "context_builder",
    "extract_linguistic_features",
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
Use linguistic_features only as deterministic evidence about morphology, vocabulary, particles, endings, and pragmatic signals.
Do not treat linguistic_features as an evaluation result, ability score, or step advancement decision.
If input_method is voice, do not penalize missing question marks or weak punctuation.
If the meaning is understandable and the step goal is achieved, return pass or soft_pass.
If the meaning is right but the expression is awkward, blunt, unnatural, or culturally risky, return soft_pass.
If the step goal is not achieved, the meaning is unclear, or the input is off-topic, return fail.

Do not mark a cultural issue unless the learner input clearly contains one.

Return only valid JSON with exactly these fields:
{
  "evaluation_result": "pass" | "soft_pass" | "fail",
  "inferred_intent_text": "short explanation of inferred learner intent",
  "issue_tags": ["grammar" | "vocabulary" | "politeness" | "naturalness" | "culturalContext" | "taskExpression" | "clarity" | "offTopic"],
  "evaluation_reason_text": "short reason for the evaluation"
}
""".strip()

RESPONSE_PACK_SYSTEM_INSTRUCTION = """
당신은 한국어 롤플레잉 학습 게임의 응답 생성기입니다. 현재 장면의 `character`로서 학습자의 최근 발화에 자연스럽게 반응하고, 확정된 진행 방향에 맞는 다음 메시지를 생성하세요.

## 입력 우선순위
1. `progress_outcome`: 대화를 현재 단계에서 유지할지, 다음 단계로 이동할지, 종료할지를 결정합니다.
2. `generation_policy`: 이번 응답의 목적과 힌트·교정·종료 메시지 생성 여부를 결정합니다.
3. `judge_result`: 이미 확정된 평가입니다. 다시 판정하거나 새로운 오류를 추가하지 마세요.
4. `learner_input_text`, `recent_messages`: 학습자의 발화와 직전 대화에 직접 반응하는 데 사용합니다.
5. `current_step`, `next_step`, `character`, `location`: 대화 목표, 캐릭터 말투와 상황 제약을 유지하는 데 사용합니다.

`generation_policy`는 생성할 메시지 유형을 결정하고, `progress_outcome`은 대화가 향할 단계를 결정합니다.

## 진행 방향
* `advance_to_next_step`: 학습자의 발화에 먼저 자연스럽게 반응한 뒤 `next_step` 목표를 유도하세요.
* `stay_current_step`: `current_step`을 유지하며 학습자가 다시 말할 기회를 주세요.
* `complete_session`: 현재 관계와 장면에 맞게 자연스럽게 대화를 마무리하세요.
* `fail_session`: 캐릭터 역할을 유지한 채 짧고 자연스럽게 상황을 종료하세요.

다음 단계로 이동할 때는 `current_step` 내용을 다시 요구하지 마세요. 현재 단계에 머물 때는 `next_step` 목표를 미리 유도하지 마세요.

## 캐릭터 작성 원칙
* `role_name`과 `persona_prompt`에 지정된 역할, 관계, 성격과 말투를 유지하세요.
* 학습자의 최근 발화를 무시하지 않고 반응하세요.
* 학습자 입장에서 말하거나 학습자의 대사를 대신 작성하지 마세요.
* 캐릭터가 알 수 없는 정보나 입력에 없는 사실을 만들지 마세요.
* 대사는 초급 학습자가 이해할 수 있도록 짧고 자연스럽게 작성하세요.
* 한 번에 하나의 핵심 질문이나 반응만 전달하세요.
* 학습자가 이미 제공한 정보를 다시 묻지 마세요.
* 다음 목표를 유도하되, 학습자가 말해야 할 정답 문장 전체를 알려 주지 마세요.

## 힌트와 교정

* `should_generate_hint`가 `true`일 때만 `hint`를 생성하세요.
* 힌트는 `hint_level` 범위를 넘지 않아야 하며, 정답 문장 전체를 공개하면 안 됩니다.
* 출력 문장에 “힌트 1단계” 같은 레벨명을 쓰지 마세요.
* `should_generate_correction`이 `true`일 때만 `correction_feedback`과 `correction_items`를 생성하세요.
* 교정 내용은 `judge_result.issue_tags`와 `evaluation_reason_text`에 명시된 문제만 다루세요.
* 판정을 변경하거나 입력에 없는 오류를 추가하지 마세요.
* 캐릭터 대사와 교정 피드백은 분리하세요.

## 메시지와 언어
* `roleplay_character_dialogue_text`: 캐릭터가 실제로 말하는 대사이며 `learning_language`로 작성합니다.
* `scene_text`: 꼭 필요한 장소·시간·상황 변화만 `system_language`로 작성합니다.
* `roleplay_character_action_text`: 캐릭터의 표정·몸짓·행동만 `system_language`로 작성합니다.
* `hint`, `correction_feedback`, `correction_items.reason_text`: `system_language`로 작성합니다.
* `original_text`와 `corrected_text`는 학습 언어 표현을 유지할 수 있습니다.
* 번역이 명시적으로 요구된 경우에만 `translation_json`을 작성하고, 아니면 `null`로 반환하세요.

현재 장면에 필요한 메시지만 생성하세요. 불필요한 장면 설명이나 행동을 추가하지 마세요.

## 출력 형식

반드시 유효한 JSON만 반환하세요. JSON 밖에 설명, 마크다운 또는 코드 블록을 출력하지 마세요.

{
"message_drafts": [
{
"message_type": "scene_text" | "roleplay_character_action_text" | "roleplay_character_dialogue_text" | "hint" | "correction_feedback",
"text": "앱에 표시할 최종 문장",
"translation_json": {
"en": "필요한 경우의 번역"
} | null
}
],
"correction_items": [
{
"type": "grammar" | "vocabulary" | "politeness" | "naturalness" | "culturalContext" | "taskExpression" | "clarity" | "offTopic",
"original_text": "학습자의 원래 표현",
"corrected_text": "더 적절한 표현",
"reason_text": "짧고 구체적인 교정 이유"
}
]
}

교정이 필요하지 않으면 `correction_items`는 빈 배열로 반환하세요.
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


def load_dotenv_bool(name: str, default: bool = False) -> bool:
    value = load_dotenv_value(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "y", "on"}


def api_key() -> str | None:
    return load_dotenv_value("GEMINI_API_KEY") or load_dotenv_value("GOOGLE_API_KEY")


def openai_api_key() -> str | None:
    return load_dotenv_value("OPENAI_API_KEY")


def elevenlabs_api_key() -> str | None:
    return load_dotenv_value("ELEVENLABS_API_KEY")


def google_stt_language_code() -> str:
    return load_dotenv_value("GOOGLE_STT_LANGUAGE_CODE") or "ko-KR"


def google_stt_model() -> str:
    return load_dotenv_value("GOOGLE_STT_MODEL") or "latest_short"


@lru_cache(maxsize=1)
def get_speech_client() -> Any:
    if speech is None:
        raise RuntimeError("google-cloud-speech package is not available.")
    return speech.SpeechClient()


@lru_cache(maxsize=4)
def get_elevenlabs_client(api_key_value: str) -> Any:
    if ElevenLabs is None:
        raise RuntimeError("elevenlabs package is not available.")
    return ElevenLabs(api_key=api_key_value)


def transcribe_recorded_audio(audio_bytes: bytes) -> str:
    if speech is None:
        raise RuntimeError("google-cloud-speech package is not available.")

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            sample_rate_hertz = wav_file.getframerate()
            channel_count = wav_file.getnchannels()
    except (EOFError, wave.Error) as exc:
        raise ValueError("Only WAV audio is supported.") from exc

    stt_response = get_speech_client().recognize(
        config=speech.RecognitionConfig(
            sample_rate_hertz=sample_rate_hertz,
            audio_channel_count=channel_count,
            language_code=google_stt_language_code(),
            enable_automatic_punctuation=True,
            model=google_stt_model(),
        ),
        audio=speech.RecognitionAudio(content=audio_bytes),
    )
    return " ".join(
        result.alternatives[0].transcript
        for result in stt_response.results
        if result.alternatives
    ).strip()


def text_to_speech_base64(text: str) -> tuple[str, str]:
    api_key_value = elevenlabs_api_key()
    if not api_key_value:
        raise RuntimeError("ELEVENLABS_API_KEY is required for TTS mode.")

    elevenlabs = get_elevenlabs_client(api_key_value)
    tts_audio = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id=load_dotenv_value("ELEVENLABS_VOICE_ID") or ELEVENLABS_VOICE_ID,
        model_id=load_dotenv_value("ELEVENLABS_MODEL") or ELEVENLABS_MODEL,
        output_format="mp3_44100_128",
    )

    if isinstance(tts_audio, bytes):
        audio_bytes = tts_audio
    elif isinstance(tts_audio, Iterable):
        audio_bytes = b"".join(chunk for chunk in tts_audio if isinstance(chunk, bytes))
    else:
        raise TypeError(f"Unsupported TTS response type: {type(tts_audio)!r}")

    audio_hash = hashlib.sha256(audio_bytes).hexdigest()
    audio_base64 = base64.b64encode(audio_bytes).decode("ascii")
    return audio_base64, audio_hash


def default_judge_model() -> str:
    return (
        load_dotenv_value("JUDGE_LLM_MODEL")
        or load_dotenv_value("GEMINI_JUDGE_MODEL")
        or "gemini-3.1-flash-lite"
    )


def default_response_model() -> str:
    return (
        load_dotenv_value("RESPONSE_LLM_MODEL")
        or load_dotenv_value("GEMINI_RESPONSE_MODEL")
        or "gemini-3.1-flash-lite"
    )


def model_provider(model_name: str) -> str:
    if model_name.startswith("gemini-"):
        return "gemini"
    if model_name.startswith("gpt-"):
        return "openai"
    return "unknown"


def llm_provider_error(model_name: str) -> str | None:
    provider = model_provider(model_name)
    if provider == "gemini":
        if genai is None or types is None:
            return "google-genai package is not available."
        if not api_key():
            return "No GEMINI_API_KEY or GOOGLE_API_KEY was found."
        return None
    if provider == "openai":
        if OpenAI is None:
            return "openai package is not available."
        if not openai_api_key():
            return "No OPENAI_API_KEY was found."
        return None
    return f"Unsupported LLM model: {model_name}"


def any_llm_provider_ready() -> bool:
    return any(llm_provider_error(model_name) is None for model_name in LLM_MODEL_OPTIONS.values())


def option_label_for_model(model_name: str) -> str:
    for label, value in LLM_MODEL_OPTIONS.items():
        if value == model_name:
            return label
    return next(iter(LLM_MODEL_OPTIONS))


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


def openai_structured_input(prompt: str) -> str:
    return "Return a JSON object matching the provided schema.\n\n" + prompt


def build_llm_request_trace(
    system_instruction: str,
    prompt: str,
    *,
    model_name: str,
    temperature: float = 0,
    max_output_tokens: int = 256,
    candidate_count: int = 1,
    thinking_budget: int | None = None,
) -> dict[str, Any]:
    provider = model_provider(model_name)
    actual_prompt = openai_structured_input(prompt) if provider == "openai" else prompt
    config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if provider == "gemini":
        config["response_mime_type"] = "application/json"
        config["candidate_count"] = candidate_count
        config["response_json_schema"] = "Pydantic JSON schema"
    if provider == "openai":
        config["text_format"] = "Pydantic output model"
    if provider == "gemini" and thinking_budget is not None:
        config["thinking_budget"] = thinking_budget
    return {
        "model": model_name,
        "provider": provider,
        "config": config,
        "system_instruction": system_instruction,
        "prompt": actual_prompt,
    }


def build_llm_response_trace(
    *,
    model_name: str,
    raw_response: str | None,
    used_fallback: bool,
    fallback_reason: str | None,
) -> dict[str, Any]:
    return {
        "model": model_name,
        "used_fallback": used_fallback,
        "fallback_reason": fallback_reason,
        "raw_response": raw_response or "",
        "raw_response_preview": (raw_response or "")[:1200],
    }


class JudgeLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_result: EvaluationResult
    inferred_intent_text: str
    issue_tags: list[IssueTag]
    evaluation_reason_text: str


class TranslationLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    en: str | None


class ResponseMessageLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_type: MessageType
    text: str
    translation_json: TranslationLLMOutput | None


class CorrectionItemLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: IssueTag
    original_text: str
    corrected_text: str
    reason_text: str


class ResponsePackLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_drafts: list[ResponseMessageLLMOutput]
    correction_items: list[CorrectionItemLLMOutput]


class LLMStructuredResult(Generic[StructuredOutputT]):
    def __init__(
        self,
        *,
        parsed: StructuredOutputT,
        raw_text: str,
        provider: str,
        model: str,
    ) -> None:
        self.parsed = parsed
        self.raw_text = raw_text
        self.provider = provider
        self.model = model


class LLMStructuredParseError(Exception):
    def __init__(self, exc: Exception, raw_text: str) -> None:
        self.raw_text = raw_text
        self.original_error = exc
        super().__init__(f"{type(exc).__name__}: {exc}")


for output_model in (
    JudgeLLMOutput,
    TranslationLLMOutput,
    ResponseMessageLLMOutput,
    CorrectionItemLLMOutput,
    ResponsePackLLMOutput,
):
    output_model.model_rebuild()


_last_provider_error: str | None = None


def clear_provider_error() -> None:
    global _last_provider_error
    _last_provider_error = None


def last_provider_error() -> str | None:
    return _last_provider_error


def set_provider_error(message: str | None) -> None:
    global _last_provider_error
    _last_provider_error = message


def llm_parse_error_reason(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        messages = []
        for error in exc.errors()[:3]:
            location = ".".join(str(part) for part in error.get("loc", []))
            messages.append(f"{location}: {error.get('msg')}")
        detail = "; ".join(messages) or str(exc)
    else:
        detail = str(exc)
    return f"invalid_llm_json_or_schema: {detail[:500]}"


def set_llm_error(exc: Exception) -> None:
    set_provider_error(llm_parse_error_reason(exc))


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
        "linguistic_features": {},
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
                "node_input": before,
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
    recent_messages = messages_for_session(state["roleplay_session_id"])[-3:]
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


@lru_cache(maxsize=1)
def get_kiwi_analyzer():
    if Kiwi is None:
        return None
    return Kiwi()


def extract_linguistic_features_node(state: dict[str, Any]) -> dict[str, Any]:
    linguistic_features = extract_linguistic_features(
        state["learner_input_text"],
        state["scenario_version"].get("learning_language") or "ko",
    )
    state["linguistic_features"] = linguistic_features
    set_node_output(state, {"linguistic_features": linguistic_features})
    return state


def extract_linguistic_features(text: str, learning_language: str) -> dict[str, Any]:
    if learning_language != "ko":
        return empty_linguistic_features()
    kiwi = get_kiwi_analyzer()
    if kiwi is None:
        return fallback_linguistic_features(text)
    try:
        analyzed = kiwi.analyze(text, top_n=1)
        tokens = analyzed[0][0] if analyzed else []
        return linguistic_features_from_tokens(text, tokens)
    except Exception:
        return fallback_linguistic_features(text)


def empty_linguistic_features() -> dict[str, Any]:
    return {
        "vocabulary": {
            "content_lemmas": [],
            "oov_terms": [],
        },
        "grammar_endings": {
            "predicate_lemmas": [],
            "final_endings": [],
            "negation_markers": [],
            "speech_level_candidates": [],
        },
        "particles_relations": {
            "particles": [],
            "clause_count": 0,
            "predicate_count": 0,
        },
        "pragmatic_signals": {
            "greeting_detected": False,
            "request_detected": False,
            "polite_ending_detected": False,
            "mitigation_detected": False,
        },
    }


def linguistic_features_from_tokens(text: str, tokens: list[Any]) -> dict[str, Any]:
    content_lemmas: list[str] = []
    oov_terms: list[str] = []
    predicate_lemmas: list[str] = []
    final_endings: list[str] = []
    negation_markers: list[str] = []
    particles: list[str] = []

    for token in tokens:
        form = str(getattr(token, "form", "") or "")
        tag = str(getattr(token, "tag", "") or "")
        if not form:
            continue
        if is_content_token(tag):
            append_unique(content_lemmas, form)
        if is_predicate_token(tag):
            append_unique(predicate_lemmas, form)
        if tag == "EF":
            append_unique(final_endings, form)
        if tag.startswith("J"):
            append_unique(particles, f"{form}/{tag}")
        if form in {"안", "못", "않", "말"}:
            append_unique(negation_markers, form)
        if tag in {"UNK", "UNKNOWN"}:
            append_unique(oov_terms, form)

    if "좀" in text and not any(item.startswith("좀/") for item in particles):
        append_unique(particles, "좀/JX")
    if not final_endings and text.rstrip().endswith(("요", "세요", "습니다", "습니까")):
        final_endings.append(infer_final_ending(text))

    speech_levels = infer_speech_levels(text, final_endings)
    predicate_count = len(predicate_lemmas)
    clause_count = max(1, predicate_count, text.count(",") + text.count("?") + text.count("."))
    return {
        "vocabulary": {
            "content_lemmas": content_lemmas,
            "oov_terms": oov_terms,
        },
        "grammar_endings": {
            "predicate_lemmas": predicate_lemmas,
            "final_endings": final_endings,
            "negation_markers": negation_markers,
            "speech_level_candidates": speech_levels,
        },
        "particles_relations": {
            "particles": particles,
            "clause_count": clause_count,
            "predicate_count": predicate_count,
        },
        "pragmatic_signals": pragmatic_signals(text, final_endings, particles),
    }


def fallback_linguistic_features(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    content_lemmas = [
        lemma
        for lemma, patterns in {
            "안녕": ["안녕"],
            "지우개": ["지우개"],
            "빌리": ["빌려", "빌리"],
            "주": ["주세요", "주세", "줘"],
            "이름": ["이름"],
            "사람": ["사람"],
            "학생": ["학생"],
            "회사원": ["회사원"],
        }.items()
        if any(pattern in normalized for pattern in patterns)
    ]
    predicate_lemmas = [lemma for lemma in ["빌리", "주"] if lemma in content_lemmas]
    final_endings = [infer_final_ending(text)] if text.rstrip().endswith(("요", "세요", "습니다", "습니까")) else []
    particles = [f"{particle}/JX" for particle in ["좀"] if particle in text]
    return {
        "vocabulary": {
            "content_lemmas": content_lemmas,
            "oov_terms": [],
        },
        "grammar_endings": {
            "predicate_lemmas": predicate_lemmas,
            "final_endings": final_endings,
            "negation_markers": [marker for marker in ["안", "못"] if marker in text],
            "speech_level_candidates": infer_speech_levels(text, final_endings),
        },
        "particles_relations": {
            "particles": particles,
            "clause_count": max(1, text.count(",") + text.count("?") + text.count(".")),
            "predicate_count": len(predicate_lemmas),
        },
        "pragmatic_signals": pragmatic_signals(text, final_endings, particles),
    }


def is_content_token(tag: str) -> bool:
    return tag.startswith(("N", "V", "XR", "SL"))


def is_predicate_token(tag: str) -> bool:
    return tag in {"VV", "VA", "VX", "VCP", "VCN"}


def append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def infer_final_ending(text: str) -> str:
    stripped = text.rstrip(" .?!")
    for ending in ("습니까", "습니다", "세요", "어요", "아요", "요"):
        if stripped.endswith(ending):
            return ending
    return ""


def infer_speech_levels(text: str, final_endings: list[str]) -> list[str]:
    candidates = []
    if any(ending.endswith(("요", "세요")) for ending in final_endings) or text.rstrip().endswith(("요", "세요")):
        candidates.append("haeyo")
    if any(ending.endswith(("습니다", "습니까")) for ending in final_endings) or text.rstrip().endswith(("습니다", "습니까")):
        candidates.append("hapsyo")
    return candidates


def pragmatic_signals(text: str, final_endings: list[str], particles: list[str]) -> dict[str, bool]:
    normalized = normalize_text(text)
    return {
        "greeting_detected": "안녕" in normalized or "반갑" in normalized,
        "request_detected": any(pattern in normalized for pattern in ["주세요", "빌려", "부탁"]),
        "polite_ending_detected": bool(infer_speech_levels(text, final_endings)),
        "mitigation_detected": "좀" in normalized or "혹시" in normalized or any(item.startswith("좀/") for item in particles),
    }


def judge_node(state: dict[str, Any]) -> dict[str, Any]:
    prompt = build_judge_prompt(state)
    sample_config = state.get("_sample_config", {})
    model_name = sample_config.get("judge_model") or default_judge_model()
    llm_request = build_llm_request_trace(
        JUDGE_SYSTEM_INSTRUCTION,
        prompt,
        model_name=model_name,
        max_output_tokens=200,
        thinking_budget=0,
    )
    raw_response = None
    used_fallback = True
    fallback_reason = None
    if sample_config.get("use_llm"):
        try:
            llm_result = generate_llm_structured(
                JUDGE_SYSTEM_INSTRUCTION,
                prompt,
                model_name=model_name,
                output_model=JudgeLLMOutput,
                max_output_tokens=200,
                thinking_budget=0,
            )
        except LLMStructuredParseError as exc:
            raw_response = exc.raw_text
            fallback_reason = llm_parse_error_reason(exc)
            llm_result = None
        if llm_result:
            raw_response = llm_result.raw_text
            try:
                state["judge_result"] = normalize_judge_result(llm_result.parsed.model_dump())
                used_fallback = False
            except Exception as exc:
                fallback_reason = llm_parse_error_reason(exc)
                state["judge_result"] = heuristic_judge_result(state)
        else:
            fallback_reason = fallback_reason or last_provider_error() or "empty_llm_response"
            state["judge_result"] = heuristic_judge_result(state)
    else:
        fallback_reason = "llm_disabled"
        state["judge_result"] = heuristic_judge_result(state)
    if not used_fallback:
        fallback_reason = None

    set_node_output(
        state,
        {
            "llm_request": llm_request,
            "llm_response": build_llm_response_trace(
                model_name=model_name,
                raw_response=raw_response,
                used_fallback=used_fallback,
                fallback_reason=fallback_reason,
            ),
            "judge_result": state["judge_result"],
            "used_fallback": used_fallback,
            "raw_response_preview": (raw_response or "")[:1200],
        },
    )
    return state


def build_judge_prompt(state: dict[str, Any]) -> str:
    current_step = state["current_step"]
    scenario_version = state["scenario_version"]
    prompt_payload = {
        "learner_input_text": state["learner_input_text"],
        "learning_language": scenario_version.get("learning_language"),
        "input_method": state["input_method"],
        "current_step_goal": current_step.get("step_goal"),
        "evaluation_criteria": build_step_evaluation_criteria(state),
        "linguistic_features": state.get("linguistic_features") or empty_linguistic_features(),
        "dialogue_context": build_judge_dialogue_context(state),
        "role_pragmatics": build_role_pragmatics(state),
        "representative_acceptable_answers": state.get("step_sample_answers", []),
    }
    return compact_json(prompt_payload)


def build_step_evaluation_criteria(state: dict[str, Any]) -> dict[str, Any]:
    current_step = state["current_step"]
    return {
        "step_specific_guidance": current_step.get("roleplay_guidance_text"),
    }


def build_judge_dialogue_context(state: dict[str, Any], limit: int = 4) -> list[dict[str, Any]]:
    direct_message_types = {
        "roleplay_character_dialogue_text",
        "learner_input_text",
        "hint",
        "correction_feedback",
    }
    messages = [
        {
            "speaker": message.get("sender_type"),
            "message_type": message.get("message_type"),
            "text": message.get("text_content"),
        }
        for message in state.get("recent_messages", [])
        if message.get("message_type") in direct_message_types
    ]
    return messages[-limit:]


def build_role_pragmatics(state: dict[str, Any]) -> dict[str, Any]:
    scenario_description = state["scenario"].get("description") or ""
    character = state["character"]
    return {
        "learner_role": extract_labeled_line(scenario_description, "학습자 역할") or "roleplay learner",
        "counterpart_role": character.get("role_name"),
        "relationship": extract_labeled_line(scenario_description, "관계"),
        "required_politeness": (
            extract_labeled_line(scenario_description, "기본 말투")
            or infer_required_politeness(character.get("persona_prompt") or "")
        ),
    }


def extract_labeled_line(text: str, label: str) -> str | None:
    lines = [line.strip() for line in (text or "").splitlines()]
    for index, line in enumerate(lines):
        if line.rstrip(":") != label:
            continue
        for value in lines[index + 1 :]:
            if value:
                return value
            if value == "":
                continue
    return None


def infer_required_politeness(persona_prompt: str) -> str | None:
    if "해요체" in persona_prompt:
        return "해요체"
    if "반말" in persona_prompt and "사용하지" in persona_prompt:
        return "polite speech; do not use 반말"
    return None


@lru_cache(maxsize=4)
def get_gemini_client(api_key_value: str):
    return genai.Client(api_key=api_key_value)


@lru_cache(maxsize=4)
def get_openai_client(api_key_value: str):
    return OpenAI(api_key=api_key_value)


def generate_llm_structured(
    system_instruction: str,
    prompt: str,
    *,
    model_name: str,
    output_model: type[StructuredOutputT],
    temperature: float = 0,
    max_output_tokens: int = 256,
    candidate_count: int = 1,
    thinking_budget: int | None = None,
) -> LLMStructuredResult[StructuredOutputT] | None:
    provider_error = llm_provider_error(model_name)
    if provider_error:
        set_provider_error(provider_error)
        return None
    if model_provider(model_name) == "gemini":
        return generate_gemini_structured(
            system_instruction,
            prompt,
            model_name=model_name,
            output_model=output_model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            candidate_count=candidate_count,
            thinking_budget=thinking_budget,
        )
    if model_provider(model_name) == "openai":
        return generate_openai_structured(
            system_instruction,
            prompt,
            model_name=model_name,
            output_model=output_model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
    set_provider_error(f"Unsupported LLM model: {model_name}")
    return None


def generate_gemini_structured(
    system_instruction: str,
    prompt: str,
    *,
    model_name: str,
    output_model: type[StructuredOutputT],
    temperature: float = 0,
    max_output_tokens: int = 256,
    candidate_count: int = 1,
    thinking_budget: int | None = None,
) -> LLMStructuredResult[StructuredOutputT] | None:
    key = api_key()
    if not key or genai is None or types is None:
        return None
    try:
        client = get_gemini_client(key)
        config_kwargs = {
            "system_instruction": system_instruction,
            "response_mime_type": "application/json",
            "temperature": temperature,
            "candidate_count": candidate_count,
            "max_output_tokens": max_output_tokens,
            "response_json_schema": output_model.model_json_schema(),
        }
        if thinking_budget is not None:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=thinking_budget,
            )
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        except Exception:
            if thinking_budget is None:
                raise
            config_kwargs.pop("thinking_config", None)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        raw_text = response.text or ""
        parsed = getattr(response, "parsed", None)
        try:
            if not isinstance(parsed, output_model):
                parsed = output_model.model_validate_json(raw_text)
        except Exception as exc:
            raise LLMStructuredParseError(exc, raw_text) from exc
        return LLMStructuredResult(
            parsed=parsed,
            raw_text=raw_text,
            provider="gemini",
            model=model_name,
        )
    except LLMStructuredParseError as exc:
        set_llm_error(exc)
        raise
    except Exception as exc:
        set_llm_error(exc)
        return None


def generate_openai_structured(
    system_instruction: str,
    prompt: str,
    *,
    model_name: str,
    output_model: type[StructuredOutputT],
    temperature: float = 0,
    max_output_tokens: int = 256,
) -> LLMStructuredResult[StructuredOutputT] | None:
    key = openai_api_key()
    if not key or OpenAI is None:
        return None
    try:
        client = get_openai_client(key)
        response = client.responses.parse(
            model=model_name,
            instructions=system_instruction,
            input=openai_structured_input(prompt),
            text_format=output_model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        output_text = getattr(response, "output_text", None)
        raw_text = output_text or ""
        parsed = getattr(response, "output_parsed", None)
        try:
            if not isinstance(parsed, output_model):
                parsed = output_model.model_validate_json(raw_text)
        except Exception as exc:
            raise LLMStructuredParseError(exc, raw_text) from exc
        return LLMStructuredResult(
            parsed=parsed,
            raw_text=raw_text,
            provider="openai",
            model=model_name,
        )
    except LLMStructuredParseError as exc:
        set_llm_error(exc)
        raise
    except Exception as exc:
        set_llm_error(exc)
        return None


def normalize_judge_result(result: dict[str, Any]) -> dict[str, Any]:
    evaluation_result = result.get("evaluation_result")
    issue_tags = list(result.get("issue_tags") or [])
    normalized = {
        "evaluation_result": evaluation_result,
        "inferred_intent_text": str(result.get("inferred_intent_text") or ""),
        "issue_tags": issue_tags,
        "evaluation_reason_text": str(result.get("evaluation_reason_text") or ""),
    }
    if evaluation_result == "pass":
        normalized["step_goal_matched"] = True
        normalized["communication_success"] = True
        normalized["correction_needed"] = False
    elif evaluation_result == "soft_pass":
        normalized["step_goal_matched"] = True
        normalized["communication_success"] = True
        normalized["correction_needed"] = True
    elif evaluation_result == "fail":
        normalized["step_goal_matched"] = False
        normalized["communication_success"] = False
        normalized["correction_needed"] = False
    else:
        raise ValueError("Judge Node returned an invalid evaluation_result.")
    normalized["cultural_issue_detected"] = "culturalContext" in issue_tags
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
                "inferred_intent_text": "The learner appears to answer the current step goal.",
                "issue_tags": [] if evaluation == "pass" else ["naturalness"],
                "evaluation_reason_text": "Local fallback matched the learner input to this step's expected intent.",
            }
        )
    return normalize_judge_result(
        {
            "evaluation_result": "fail",
            "inferred_intent_text": "The learner input does not clearly satisfy the current step.",
            "issue_tags": ["clarity"],
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
    sample_config = state.get("_sample_config", {})
    rule_decision = state["rule_decision"]
    state["next_step"] = (
        serialize_step(find_one(sample_db.STEPS, "step_id", rule_decision["next_step_id"]))
        if rule_decision.get("next_step_id")
        else None
    )
    prompt = build_response_pack_prompt(state)
    model_name = sample_config.get("response_model") or default_response_model()
    llm_request = build_llm_request_trace(
        RESPONSE_PACK_SYSTEM_INSTRUCTION,
        prompt,
        model_name=model_name,
        max_output_tokens=RESPONSE_PACK_MAX_OUTPUT_TOKENS,
    )
    raw_response = None
    used_fallback = True
    fallback_reason = None
    response_pack = {"message_drafts": [], "correction_items": []}
    if sample_config.get("use_llm"):
        try:
            llm_result = generate_llm_structured(
                RESPONSE_PACK_SYSTEM_INSTRUCTION,
                prompt,
                model_name=model_name,
                output_model=ResponsePackLLMOutput,
                max_output_tokens=RESPONSE_PACK_MAX_OUTPUT_TOKENS,
            )
        except LLMStructuredParseError as exc:
            raw_response = exc.raw_text
            fallback_reason = llm_parse_error_reason(exc)
            llm_result = None
        if llm_result:
            raw_response = llm_result.raw_text
            try:
                response_pack = llm_result.parsed.model_dump()
                used_fallback = False
            except Exception as exc:
                fallback_reason = llm_parse_error_reason(exc)
                response_pack = {"message_drafts": [], "correction_items": []}
        else:
            fallback_reason = fallback_reason or last_provider_error() or "empty_llm_response"
    else:
        fallback_reason = "llm_disabled"
    if not used_fallback:
        fallback_reason = None
    response_pack = normalize_response_pack(state, response_pack)
    response_pack = ensure_minimum_response_pack(state, response_pack)
    response_pack = normalize_response_pack(state, response_pack)
    state["response_pack"] = response_pack
    set_node_output(
        state,
        {
            "llm_request": llm_request,
            "llm_response": build_llm_response_trace(
                model_name=model_name,
                raw_response=raw_response,
                used_fallback=used_fallback,
                fallback_reason=fallback_reason,
            ),
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
        "languages": {
            "learning_language": state["scenario_version"].get("learning_language"),
            "system_language": state["scenario_version"].get("default_system_language"),
        },
        "current_step": response_step_context(state["current_step"]),
        "next_step": response_step_context(state.get("next_step")) if state.get("next_step") else None,
        "character": response_character_context(state),
        "location": response_location_context(state),
        "recent_messages": response_recent_context(state),
        "learner_input_text": state["learner_input_text"],
        "judge_result": state["judge_result"],
        "generation_policy": response_generation_policy(state),
        "progress_outcome": rule_decision["progress_outcome"],
    }
    return compact_json(prompt_payload)


def response_step_context(step: dict[str, Any] | None) -> dict[str, Any] | None:
    if not step:
        return None
    return {
        "step_goal": step.get("step_goal"),
        "guidance": step.get("roleplay_guidance_text"),
    }


def response_character_context(state: dict[str, Any]) -> dict[str, Any]:
    character = state["character"]
    return {
        "character_name": character.get("character_name"),
        "role_name": character.get("role_name"),
        "persona_prompt": character.get("persona_prompt"),
    }


def response_location_context(state: dict[str, Any]) -> dict[str, Any]:
    location = state["location"]
    return {
        "location_prompt": location.get("location_prompt"),
    }


def response_recent_context(state: dict[str, Any], limit: int = 4) -> list[dict[str, Any]]:
    direct_message_types = {
        "roleplay_character_dialogue_text",
        "learner_input_text",
        "hint",
        "correction_feedback",
    }
    return [
        {
            "speaker": message.get("sender_type"),
            "message_type": message.get("message_type"),
            "text": message.get("text_content"),
        }
        for message in state.get("recent_messages", [])
        if message.get("message_type") in direct_message_types
    ][-limit:]


def response_generation_policy(state: dict[str, Any]) -> dict[str, Any]:
    rule_decision = state["rule_decision"]
    judge_result = state["judge_result"]
    should_generate_hint = bool(
        rule_decision["progress_outcome"] in {"stay_current_step", "fail_session"}
        and judge_result
        and judge_result["evaluation_result"] == "fail"
    )
    should_generate_correction = bool(
        judge_result
        and judge_result["evaluation_result"] == "soft_pass"
        and judge_result["correction_needed"]
    )
    return {
        "main_task": response_main_task(rule_decision["progress_outcome"]),
        "should_generate_hint": should_generate_hint,
        "hint_level": rule_decision["hint_level"] if should_generate_hint else None,
        "should_generate_correction": should_generate_correction,
        "should_generate_completion": rule_decision["progress_outcome"] == "complete_session",
    }


def response_main_task(progress_outcome: str) -> str:
    if progress_outcome == "advance_to_next_step":
        return "Naturally acknowledge the learner and lead into the next step."
    if progress_outcome == "stay_current_step":
        return "Help the learner try the current step again."
    if progress_outcome == "fail_session":
        return "Close the failed attempt briefly and kindly."
    if progress_outcome == "complete_session":
        return "Give a concise completion response."
    return "Continue the roleplay naturally."


def normalize_response_pack(state: dict[str, Any], response_pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_drafts": [
            normalize_message_draft(state, draft)
            for draft in response_pack.get("message_drafts", [])
            if isinstance(draft, dict)
        ],
        "correction_items": [
            item
            for item in response_pack.get("correction_items", [])
            if isinstance(item, dict)
        ],
    }


def normalize_message_draft(state: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    message_type = draft.get("message_type")
    text_content = draft.get("text_content") or draft.get("text") or ""
    normalized = {
        "message_type": message_type,
        "text_content": text_content,
        "text_language": language_for_message_type(state, message_type),
        "translation_json": parse_json_maybe(draft.get("translation_json")),
        "step_id": target_step_id_for_message_type(state, message_type),
        "scenario_roleplay_character_id": scenario_character_id_for_message_type(state, message_type),
        "hint_level": hint_level_for_message_type(state, draft),
    }
    return normalized


def language_for_message_type(state: dict[str, Any], message_type: str | None) -> str:
    if message_type == "roleplay_character_dialogue_text":
        return learning_language(state)
    return system_language(state)


def target_step_id_for_message_type(state: dict[str, Any], message_type: str | None) -> str | None:
    rule_decision = state["rule_decision"]
    if message_type in {"hint", "correction_feedback"}:
        return state["current_step"].get("step_id")
    if (
        message_type in {"scene_text", "roleplay_character_action_text", "roleplay_character_dialogue_text"}
        and rule_decision["progress_outcome"] == "advance_to_next_step"
        and rule_decision.get("next_step_id")
    ):
        return rule_decision["next_step_id"]
    return state["current_step"].get("step_id")


def scenario_character_id_for_message_type(state: dict[str, Any], message_type: str | None) -> str | None:
    if message_type in {"roleplay_character_action_text", "roleplay_character_dialogue_text"}:
        return state["character"].get("scenario_roleplay_character_id")
    return None


def hint_level_for_message_type(state: dict[str, Any], draft: dict[str, Any]) -> str | None:
    if draft.get("message_type") != "hint":
        return None
    return state["rule_decision"].get("hint_level") or draft.get("hint_level") or "light"


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
    errors.extend(validate_message_types(response_pack))
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
        response_pack = normalize_response_pack(state, response_pack)
        fallback_errors.extend(validate_message_types(response_pack))
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


def validate_message_types(response_pack: dict[str, Any]) -> list[str]:
    allowed = {
        "scene_text",
        "roleplay_character_action_text",
        "roleplay_character_dialogue_text",
        "hint",
        "correction_feedback",
    }
    return [
        f"message_drafts[{index}].message_type is invalid."
        for index, draft in enumerate(response_pack.get("message_drafts", []))
        if draft.get("message_type") not in allowed
    ]


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
        expected_language = expected.get(draft.get("message_type"))
        if expected_language is None:
            continue
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


@lru_cache(maxsize=1)
def build_graph_runner() -> Callable[[dict[str, Any]], dict[str, Any]]:
    node_functions = {
        "context_builder": timed_node("context_builder", context_builder_node),
        "extract_linguistic_features": timed_node(
            "extract_linguistic_features",
            extract_linguistic_features_node,
        ),
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
    graph.add_edge("context_builder", "extract_linguistic_features")
    graph.add_edge("extract_linguistic_features", "judge")
    graph.add_edge("judge", "game_rule_engine")
    graph.add_edge("game_rule_engine", "response_pack")
    graph.add_edge("response_pack", "response_validator")
    graph.add_edge("response_validator", "domain_persistence")
    graph.add_edge("domain_persistence", END)
    compiled = graph.compile()
    return compiled.invoke


def warmup_sample_roleplay_runtime(
    *,
    include_llm: bool | None = None,
    judge_model: str | None = None,
    response_model: str | None = None,
) -> dict[str, Any]:
    if include_llm is None:
        include_llm = load_dotenv_bool("ROLEPLAY_SAMPLE_LLM_WARMUP", True)
    return _cached_warmup_sample_roleplay_runtime(
        include_llm,
        judge_model or default_judge_model(),
        response_model or default_response_model(),
    )


@lru_cache(maxsize=8)
def _cached_warmup_sample_roleplay_runtime(
    include_llm: bool,
    judge_model: str,
    response_model: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    steps: list[dict[str, Any]] = []

    def record(name: str, fn: Callable[[], Any]) -> None:
        step_started = time.perf_counter()
        try:
            fn()
            steps.append(
                {
                    "name": name,
                    "ok": True,
                    "elapsed_ms": round((time.perf_counter() - step_started) * 1000, 2),
                }
            )
        except Exception as exc:
            steps.append(
                {
                    "name": name,
                    "ok": False,
                    "elapsed_ms": round((time.perf_counter() - step_started) * 1000, 2),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    record("runtime_tables", ensure_runtime_tables)
    record("graph_runner", build_graph_runner)
    record("kiwi_analyzer", get_kiwi_analyzer)
    if speech is not None:
        record("google_speech_client", get_speech_client)
    if elevenlabs_api_key():
        record("elevenlabs_client", lambda: get_elevenlabs_client(elevenlabs_api_key() or ""))
    if llm_provider_error(judge_model) is None:
        record("judge_llm_client", lambda: _warmup_llm_client(judge_model))
    if response_model != judge_model and llm_provider_error(response_model) is None:
        record("response_llm_client", lambda: _warmup_llm_client(response_model))
    if include_llm:
        record("judge_llm_network", lambda: _warmup_judge_llm_network(judge_model))
        record("response_llm_network", lambda: _warmup_response_llm_network(response_model))

    return {
        "include_llm": include_llm,
        "judge_model": judge_model,
        "response_model": response_model,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "steps": steps,
    }


def _warmup_llm_client(model_name: str) -> None:
    provider = model_provider(model_name)
    if provider == "gemini":
        key = api_key()
        if key:
            get_gemini_client(key)
    elif provider == "openai":
        key = openai_api_key()
        if key:
            get_openai_client(key)


def _warmup_judge_llm_network(model_name: str) -> None:
    clear_provider_error()
    result = generate_llm_structured(
        JUDGE_SYSTEM_INSTRUCTION,
        compact_json(
            {
                "learner_input_text": "안녕하세요.",
                "learning_language": "ko",
                "input_method": "text",
                "current_step_goal": "Warm up the roleplay judge model.",
                "evaluation_criteria": {"step_specific_guidance": "Return a valid pass judgment."},
                "linguistic_features": empty_linguistic_features(),
                "dialogue_context": [],
                "role_pragmatics": {"required_politeness": "polite speech"},
                "representative_acceptable_answers": ["안녕하세요."],
            }
        ),
        model_name=model_name,
        output_model=JudgeLLMOutput,
        max_output_tokens=160,
        thinking_budget=0,
    )
    if result is None:
        raise RuntimeError(last_provider_error() or "judge LLM warm-up returned no response.")


def _warmup_response_llm_network(model_name: str) -> None:
    clear_provider_error()
    result = generate_llm_structured(
        RESPONSE_PACK_SYSTEM_INSTRUCTION,
        compact_json(
            {
                "languages": {
                    "learning_language": "ko",
                    "system_language": "en",
                },
                "current_step": {
                    "step_goal": "Warm up the response model.",
                    "guidance": "Return one short character dialogue.",
                },
                "next_step": None,
                "character": {
                    "character_name": "Yujin",
                    "role_name": "classmate",
                    "persona_prompt": "Use short, friendly, polite Korean.",
                },
                "location": {"location_prompt": "A campus classroom."},
                "recent_messages": [],
                "learner_input_text": "안녕하세요.",
                "judge_result": normalize_judge_result(
                    {
                        "evaluation_result": "pass",
                        "inferred_intent_text": "The learner greets the character.",
                        "issue_tags": [],
                        "evaluation_reason_text": "Warm-up prompt.",
                    }
                ),
                "generation_policy": {
                    "main_task": "Continue the roleplay naturally.",
                    "should_generate_hint": False,
                    "hint_level": None,
                    "should_generate_correction": False,
                    "should_generate_completion": False,
                },
                "progress_outcome": "stay_current_step",
            }
        ),
        model_name=model_name,
        output_model=ResponsePackLLMOutput,
        max_output_tokens=260,
    )
    if result is None:
        raise RuntimeError(last_provider_error() or "response LLM warm-up returned no response.")


def run_roleplay_turn(
    text: str,
    *,
    roleplay_session_id: str,
    use_llm: bool,
    judge_model: str,
    response_model: str,
    input_method: str = INPUT_METHOD,
) -> dict[str, Any]:
    clear_provider_error()
    state = build_initial_state(
        roleplay_session_id=roleplay_session_id,
        learner_id=LEARNER_ID,
        learner_input_text=text,
        input_method=input_method,
    )
    state["_sample_config"] = {
        "use_llm": use_llm,
        "judge_model": judge_model,
        "response_model": response_model,
    }
    runner = build_graph_runner()
    return runner(state)


def current_session(roleplay_session_id: str) -> dict[str, Any]:
    return find_one(sample_db.ROLEPLAY_SESSIONS, "roleplay_session_id", roleplay_session_id)


def current_step_for_session(roleplay_session_id: str) -> dict[str, Any]:
    session = current_session(roleplay_session_id)
    return find_one(sample_db.STEPS, "step_id", session["current_step_id"])


