from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import get_settings
from samples.agents.sample_roleplaying import sample_roleplaying_backend


settings = get_settings()

app = FastAPI(title=settings.app_title)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def warmup_sample_roleplay_runtime() -> None:
    sample_roleplaying_backend.warmup_sample_roleplay_runtime()


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
