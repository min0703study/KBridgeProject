from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from backend.app.agents.base import AgentError
from backend.app.core.config import get_settings


class ReviewKeywordJson(BaseModel):
    positive: list[str] = Field(default_factory=list, max_length=8)
    negative: list[str] = Field(default_factory=list, max_length=8)
    neutral: list[str] = Field(default_factory=list, max_length=8)
    care_tasks: list[str] = Field(default_factory=list, max_length=8)
    operation_issues: list[str] = Field(default_factory=list, max_length=8)
    risk_flags: list[str] = Field(default_factory=list, max_length=8)


class ReviewAnalysisOutput(BaseModel):
    sentiment: Literal["positive", "neutral", "negative", "mixed"]
    summary: str = Field(max_length=700)
    ai_score: float = Field(ge=0, le=5)
    ai_score_reason: str = Field(max_length=700)
    keyword_json: ReviewKeywordJson
    reply_message: str = Field(max_length=500)
    requires_operator_check: bool = False


SYSTEM_INSTRUCTION = """
너는 DUSON 사후 관리/평가 분석 Agent다.

역할:
- 간병 서비스 종료 후 고객 또는 보호자가 남긴 평가를 운영자가 빠르게 확인할 수 있도록 구조화한다.
- DB context와 고객 평가 원문에 있는 사실만 근거로 요약, 키워드, 점수, 답변 초안을 만든다.

중요 규칙:
- 의료 판단, 학대, 의료 사고, 법적 책임을 단정하지 않는다.
- 위험 신호가 있으면 risk_flags에만 표시하고 requires_operator_check=true로 둔다.
- 고객 답변 초안에는 전화번호, 주소, 주민등록번호, 건강정보 등 과도한 개인정보를 노출하지 않는다.
- 간병사 또는 고객을 비난하는 표현을 쓰지 않고, 공감과 개선 안내 중심으로 작성한다.
- 점수는 0.0~5.0 범위로 산정한다.
- 반드시 JSON 객체만 반환한다.
"""


class ReviewAnalysisAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: genai.Client | None = None

    async def run(self, *, raw_message: str, context: dict[str, Any]) -> ReviewAnalysisOutput:
        if not raw_message.strip():
            raise AgentError("고객 평가 원문이 비어 있어 리뷰 분석을 실행할 수 없습니다.")
        return await asyncio.to_thread(self._run_sync, raw_message, context)

    def _run_sync(self, raw_message: str, context: dict[str, Any]) -> ReviewAnalysisOutput:
        prompt = self._build_prompt(raw_message=raw_message, context=context)
        response = None
        try:
            response = self._client_or_create().models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=ReviewAnalysisOutput,
                    temperature=0,
                    top_p=0.8,
                    max_output_tokens=self.settings.gemini_max_output_tokens,
                ),
            )
            if getattr(response, "parsed", None) is not None:
                return ReviewAnalysisOutput.model_validate(response.parsed)
            return ReviewAnalysisOutput.model_validate_json(response.text or "")
        except ValidationError as exc:
            raise AgentError(f"리뷰 분석 결과 스키마 검증에 실패했습니다: {exc}") from exc
        except Exception as exc:
            raw_text = getattr(response, "text", None)
            suffix = f" raw={raw_text[:300]}" if raw_text else ""
            raise AgentError(f"Gemini 리뷰 분석 호출에 실패했습니다: {exc}{suffix}") from exc

    def _build_prompt(self, *, raw_message: str, context: dict[str, Any]) -> str:
        return "\n".join(
            [
                "DB_CONTEXT_JSON:",
                json.dumps(context, ensure_ascii=False, default=str),
                "",
                "CUSTOMER_REVIEW_RAW_MESSAGE:",
                raw_message,
                "",
                "OUTPUT_REQUIREMENT:",
                "sentiment, summary, ai_score, ai_score_reason, keyword_json, reply_message, requires_operator_check를 채운다.",
            ]
        )

    def _client_or_create(self) -> genai.Client:
        if self._client is None:
            if not self.settings.gemini_api_key:
                raise AgentError("GEMINI_API_KEY 또는 GOOGLE_API_KEY가 설정되지 않았습니다.")
            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client
