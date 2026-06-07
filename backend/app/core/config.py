from functools import lru_cache
from os import getenv

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class Settings(BaseModel):
    app_title: str = "KBridge Roleplay API"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    gemini_model: str = getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    elevenlabs_model: str = getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")
    elevenlabs_voice_id: str = getenv("ELEVENLABS_VOICE_ID", "iP95p4xoKVk53GoZ742B")
    google_stt_language_code: str = getenv("GOOGLE_STT_LANGUAGE_CODE", "ko-KR")
    google_stt_model: str = getenv("GOOGLE_STT_MODEL", "latest_short")
    gemini_api_key: str | None = getenv("GEMINI_API_KEY") or getenv("GOOGLE_API_KEY")
    elevenlabs_api_key: str | None = getenv("ELEVENLABS_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
