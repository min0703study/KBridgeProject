from __future__ import annotations

import base64
import io
import re
import wave
from collections.abc import Iterable

from elevenlabs.client import ElevenLabs
from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import speech

from backend.app.core.config import get_settings


class InvalidAudioError(ValueError):
    pass


class EmptyTranscriptError(ValueError):
    pass


class MissingProviderKeyError(RuntimeError):
    pass


def transcribe_wav_audio(audio_bytes: bytes) -> str:
    if not audio_bytes:
        raise InvalidAudioError("Uploaded audio is empty.")

    transcript = _transcribe_wav(audio_bytes)
    if not transcript:
        raise EmptyTranscriptError("Google STT returned an empty transcript.")

    return _normalize_korean_stt_transcript(transcript)


def text_to_speech_base64(text: str) -> str:
    settings = get_settings()
    if not settings.elevenlabs_api_key:
        raise MissingProviderKeyError("ELEVENLABS_API_KEY is required.")

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


def _transcribe_wav(audio_bytes: bytes) -> str:
    settings = get_settings()

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            sample_rate_hertz = wav_file.getframerate()
            channel_count = wav_file.getnchannels()
    except (EOFError, wave.Error) as exc:
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


def _normalize_korean_stt_transcript(transcript: str) -> str:
    normalized = transcript.strip()
    normalized = re.sub(r"^내\s+(총)\b", r"네, \1", normalized)
    normalized = re.sub(r"^내\s+(결제)\b", r"네, \1", normalized)
    normalized = re.sub(r"^내\s+(완료)\b", r"네, \1", normalized)
    return normalized
