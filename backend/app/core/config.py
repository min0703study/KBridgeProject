from functools import lru_cache
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_title: str = "KBridge API"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    database_url: str | None = os.getenv("DATABASE_URL")
    gemini_model: str = "gemini-3.1-pro-preview"
    elevenlabs_model: str = "eleven_flash_v2_5"
    elevenlabs_voice_id: str = "iP95p4xoKVk53GoZ742B"
    google_stt_language_code: str = "ko-KR"
    google_stt_model: str = "latest_short"
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    roleplay_node_trace_log: bool = False

    # 허브(k_bridge_admin) 신호 발신 — 둘 다 설정된 경우에만 활성 (없으면 no-op)
    kbridge_hub_url: str | None = None
    kbridge_ingest_secret: str | None = None

    @property
    def resolved_gemini_api_key(self) -> str | None:
        return self.gemini_api_key or self.google_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
