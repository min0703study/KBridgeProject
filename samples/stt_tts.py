from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

try:
    from elevenlabs.play import play
except Exception:  # pragma: no cover - optional local audio playback.
    play = None


OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "stt_tts_voice_preview"
DEFAULT_TEXT = "안녕하세요. 잠시만 기다려 주시겠어요?"
DEFAULT_MODEL = "eleven_flash_v2_5"
DEFAULT_GENDER = "male"
FALLBACK_MALE_PREMADE_VOICES = [
    {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam"},
    {"voice_id": "ErXwobaYiN019PkySvjV", "name": "Antoni"},
    {"voice_id": "VR6AewLTigWG4xSOukaG", "name": "Arnold"},
    {"voice_id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie"},
    {"voice_id": "iP95p4xoKVk53GoZ742B", "name": "Chris"},
    {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "name": "George"},
    {"voice_id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh"},
    {"voice_id": "TX3LPaxmHKxFdv7VOQHJ", "name": "Liam"},
    {"voice_id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam"},
]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "y", "on"}


def audio_to_bytes(audio: bytes | Iterable[bytes]) -> bytes:
    if isinstance(audio, bytes):
        return audio
    return b"".join(chunk for chunk in audio if isinstance(chunk, bytes))


def label_value(voice: object, key: str) -> str:
    labels = getattr(voice, "labels", None) or {}
    if isinstance(labels, dict):
        return str(labels.get(key) or "").strip().casefold()
    return str(getattr(labels, key, "") or "").strip().casefold()


def safe_filename(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value.strip())
    return safe.strip("_") or "voice"


def voice_matches(voice: object, *, gender: str) -> bool:
    if getattr(voice, "category", None) != "premade":
        return False
    if gender == "any":
        return True
    return label_value(voice, "gender") == gender


def env_int(name: str) -> int | None:
    value = os.getenv(name)
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def load_preview_voices(elevenlabs: ElevenLabs, *, gender: str) -> list[object]:
    try:
        return [
            voice
            for voice in elevenlabs.voices.get_all().voices
            if voice_matches(voice, gender=gender)
        ]
    except Exception as exc:
        if gender != "male":
            raise
        print(f"Could not read ElevenLabs voice list: {type(exc).__name__}: {exc}")
        print("Falling back to known male premade voice IDs.")
        return FALLBACK_MALE_PREMADE_VOICES


def voice_id_and_name(voice: object) -> tuple[str, str]:
    if isinstance(voice, dict):
        voice_id = str(voice.get("voice_id") or "")
        return voice_id, str(voice.get("name") or voice_id)
    voice_id = str(getattr(voice, "voice_id", "") or "")
    return voice_id, str(getattr(voice, "name", "") or voice_id)


def main() -> None:
    load_dotenv()

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is required. Add it to .env or your shell environment.")

    text = os.getenv("STT_TTS_TEXT") or DEFAULT_TEXT
    gender = (os.getenv("STT_TTS_VOICE_GENDER") or DEFAULT_GENDER).strip().casefold()
    model_id = os.getenv("ELEVENLABS_MODEL") or DEFAULT_MODEL
    voice_limit = env_int("STT_TTS_VOICE_LIMIT")
    should_play = env_bool("STT_TTS_PLAY_AUDIO", True)

    elevenlabs = ElevenLabs(api_key=api_key)
    voices = load_preview_voices(elevenlabs, gender=gender)
    if voice_limit:
        voices = voices[:voice_limit]
    if not voices:
        raise RuntimeError(f"No {gender!r} premade voices were found.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Previewing {len(voices)} {gender} premade voice(s) with model_id={model_id}")
    for index, voice in enumerate(voices, start=1):
        voice_id, voice_name = voice_id_and_name(voice)
        print(f"{index:02d}. {voice_name} ({voice_id})")

        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format="mp3_44100_128",
        )
        audio_bytes = audio_to_bytes(audio)
        output_path = OUTPUT_DIR / f"{index:02d}_{safe_filename(voice_name)}_{voice_id}.mp3"
        output_path.write_bytes(audio_bytes)
        print(f"    saved {len(audio_bytes):,} bytes to {output_path}")

        if should_play and play is not None:
            play(audio_bytes)


if __name__ == "__main__":
    main()
