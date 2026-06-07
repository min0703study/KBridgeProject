from __future__ import annotations

import base64
import io
import json
import wave
from collections.abc import Iterable

from elevenlabs.client import ElevenLabs
from google import genai
from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import speech
from google.genai import types

from backend.app.core.config import get_settings
from backend.app.schemas.roleplay import (
    AssistantMessage,
    CorrectionFeedback,
    Evaluation,
    RoleplayTurnResponse,
    RoleplayUiState,
)


class InvalidAudioError(ValueError):
    pass


class EmptyTranscriptError(ValueError):
    pass


class MissingProviderKeyError(RuntimeError):
    pass


SYSTEM_INSTRUCTION = """
You are a temporary UI-test roleplay agent for a Korean learning app used by Filipino young adults.
Scenario: The learner is a convenience store clerk. The customer is buying snacks and beer.
Current step goal: The learner should politely ask to check the customer's ID.

Return only valid JSON with this exact shape:
{
  "evaluation_result": "pass" | "soft_pass" | "fail",
  "issue_tags": ["grammar" | "vocabulary" | "politeness" | "naturalness" | "culturalContext" | "taskExpression" | "clarity"],
  "correction_needed": true | false,
  "assistant_ko": "short Korean customer reply",
  "assistant_en": "short English translation",
  "feedback": null | {
    "previous_text": "learner transcript or problematic phrase",
    "better_way": "better Korean sentence",
    "politeness_note": "short English explanation",
    "grammar_note": "short English explanation"
  }
}

Judge generously by intent. If the learner asks for ID but sounds blunt or unnatural, use soft_pass.
If the learner does not address ID checking, use fail and guide them back as the customer.
Keep assistant_ko under 45 Korean characters and assistant_en under 90 English characters.
""".strip()


async def run_convenience_store_turn(
    *,
    audio_bytes: bytes,
    filename: str | None,
    scenario_id: str | None,
    step_id: str | None,
    client_turn_id: str | None,
) -> RoleplayTurnResponse:
    if not audio_bytes:
        raise InvalidAudioError("Uploaded audio is empty.")

    settings = get_settings()
    if not settings.resolved_gemini_api_key:
        raise MissingProviderKeyError("GEMINI_API_KEY or GOOGLE_API_KEY is required.")
    if not settings.elevenlabs_api_key:
        raise MissingProviderKeyError("ELEVENLABS_API_KEY is required.")

    transcript = _transcribe_wav(audio_bytes)
    if not transcript:
        raise EmptyTranscriptError("Google STT returned an empty transcript.")

    response_pack = _generate_response_pack(transcript)
    audio_base64 = _text_to_speech_base64(response_pack["assistant_ko"])

    result = response_pack.get("evaluation_result", "soft_pass")
    correction_needed = bool(response_pack.get("correction_needed"))
    feedback_payload = response_pack.get("feedback") if correction_needed else None

    feedback = None
    if isinstance(feedback_payload, dict):
        feedback = CorrectionFeedback(
            previous_text=str(feedback_payload.get("previous_text") or transcript),
            better_way=str(
                feedback_payload.get("better_way")
                or "죄송하지만, 신분증 확인 부탁드립니다."
            ),
            politeness_note=str(
                feedback_payload.get("politeness_note")
                or "Use a softer request when speaking to a customer."
            ),
            grammar_note=str(
                feedback_payload.get("grammar_note")
                or "Use '신분증 확인' for a natural ID-check request."
            ),
        )

    return RoleplayTurnResponse(
        transcript=transcript,
        assistant_message=AssistantMessage(
            ko=str(response_pack.get("assistant_ko") or "네, 여기 있습니다."),
            en=str(response_pack.get("assistant_en") or "Sure, here it is."),
            audio_base64=audio_base64,
        ),
        evaluation=Evaluation(
            result=result if result in {"pass", "soft_pass", "fail"} else "soft_pass",
            issue_tags=[
                tag
                for tag in response_pack.get("issue_tags", [])
                if tag
                in {
                    "grammar",
                    "vocabulary",
                    "politeness",
                    "naturalness",
                    "culturalContext",
                    "taskExpression",
                    "clarity",
                }
            ],
            correction_needed=correction_needed,
        ),
        feedback=feedback,
        ui_state=RoleplayUiState(
            remaining_chances=5,
            score_count=0,
            current_step_label="Step 1: Check your ID.",
            should_show_feedback=feedback is not None,
        ),
    )


def _transcribe_wav(audio_bytes: bytes) -> str:
    settings = get_settings()

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            sample_rate_hertz = wav_file.getframerate()
            channel_count = wav_file.getnchannels()
    except wave.Error as exc:
        raise InvalidAudioError("Only WAV audio is supported for this MVP endpoint.") from exc

    try:
        speech_client = speech.SpeechClient()
        stt_response = speech_client.recognize(
            config=speech.RecognitionConfig(
                sample_rate_hertz=sample_rate_hertz,
                audio_channel_count=channel_count,
                language_code=settings.google_stt_language_code,
                enable_automatic_punctuation=True,
                model=settings.google_stt_model,
            ),
            audio=speech.RecognitionAudio(content=audio_bytes),
        )
    except (GoogleAPICallError, RetryError) as exc:
        raise InvalidAudioError(f"Google STT failed: {exc}") from exc

    return " ".join(
        result.alternatives[0].transcript
        for result in stt_response.results
        if result.alternatives
    ).strip()


def _generate_response_pack(transcript: str) -> dict:
    settings = get_settings()
    prompt = f'Learner transcript: "{transcript}"'
    client = genai.Client(api_key=settings.resolved_gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
        ),
    )

    raw_text = (response.text or "").strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.removeprefix("json").strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = _fallback_response_pack(transcript)

    if not isinstance(parsed, dict):
        return _fallback_response_pack(transcript)

    return parsed


def _fallback_response_pack(transcript: str) -> dict:
    return {
        "evaluation_result": "soft_pass",
        "issue_tags": ["politeness", "naturalness"],
        "correction_needed": True,
        "assistant_ko": "네, 신분증 여기 있습니다.",
        "assistant_en": "Sure, here is my ID.",
        "feedback": {
            "previous_text": transcript,
            "better_way": "죄송하지만, 신분증 확인 부탁드립니다.",
            "politeness_note": "A softer request sounds more polite in a service situation.",
            "grammar_note": "Use '신분증 확인' to describe checking an ID naturally.",
        },
    }


def _text_to_speech_base64(text: str) -> str:
    settings = get_settings()
    elevenlabs = ElevenLabs(api_key=settings.elevenlabs_api_key)
    tts_audio = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id=settings.elevenlabs_voice_id,
        model_id=settings.elevenlabs_model,
        output_format="mp3_44100_128",
    )

    if isinstance(tts_audio, bytes):
        audio_bytes = tts_audio
    elif isinstance(tts_audio, Iterable):
        audio_bytes = b"".join(chunk for chunk in tts_audio if isinstance(chunk, bytes))
    else:
        raise TypeError(f"Unsupported ElevenLabs TTS response type: {type(tts_audio)!r}")

    return base64.b64encode(audio_bytes).decode("ascii")
