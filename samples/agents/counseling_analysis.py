from __future__ import annotations

import asyncio
import json
from typing import Any
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from backend.app.agents.base import AgentError, AgentRunResult, BaseAgent
from backend.app.core.config import get_settings


class CareItem(BaseModel):
    label: str = Field(max_length=40)
    value: str = Field(max_length=120)


# 상담 녹취에서 DB에 매핑할 만한 핵심 정보를 추출하는 모델
class CounselingExtracted(BaseModel):
    caller_name: str | None = None
    caller_phone: str | None = None
    requester_name: str | None = None
    requester_relationship: Literal["SELF", "SPOUSE", "CHILD", "PARENT", "SIBLING", "RELATIVE", "LEGAL_GUARDIAN", "OTHER", "UNKNOWN"] | None = None
    requester_type: Literal["PATIENT", "GUARDIAN", "FC", "OTHER", "UNKNOWN"] | None = None
    requester_phone: str | None = None
    patient_name: str | None = None
    patient_gender: Literal["MALE", "FEMALE", "OTHER", "UNKNOWN"] | None = None
    patient_birth_date: str | None = None
    hospital_name: str | None = None
    hospital_room: str | None = None
    period_label: str | None = None
    proposed_start_datetime: str | None = None
    proposed_end_datetime: str | None = None
    proposed_daily_wage: int | None = None
    care_request_reason: str | None = None
    preferred_caregiver_gender: Literal["MALE", "FEMALE", "ANY"] | None = None
    disease_note: str | None = None
    allergy_note: str | None = None
    mobility_level: Literal["NONE", "LOW", "MEDIUM", "HIGH"] | None = None
    dementia_level: Literal["NONE", "LOW", "MEDIUM", "HIGH"] | None = None
    toileting_level: Literal["NONE", "LOW", "MEDIUM", "HIGH"] | None = None
    meal_assistance_level: Literal["NONE", "LOW", "MEDIUM", "HIGH"] | None = None
    medication_required: bool | None = None
    rehab_required: bool | None = None
    suction_required: bool | None = None
    night_care_required: bool | None = None
    infection_precaution_required: bool | None = None
    care_intensity_level: Literal["LOW", "MEDIUM", "HIGH"] | None = None
    special_note: str | None = None


class CounselingAnalysisOutput(BaseModel):
    summary: str = Field(max_length=700)
    transcript_edited_text: str = Field(max_length=4000)
    extracted: CounselingExtracted
    care_items: list[CareItem] = Field(min_length=1, max_length=12)
    confidence: float = Field(ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list, max_length=12)


SYSTEM_INSTRUCTION = """
너는 DUSON 관리자용 간병 매칭 상담 분석 Agent다.

역할:
- 상담 녹취 STT 원문에서 간병 매칭 요청 정보를 구조화한다.
- DB context와 STT 원문을 비교해 확인 가능한 정보만 추출한다.
- 의료 판단을 확정하지 말고, 상담자가 말한 사실과 운영 입력 후보만 정리한다.

중요 규칙:
- DB 컬럼에 매핑 가능한 값은 extracted에 넣는다.
- DB에 직접 저장하기 애매한 상담 참고 내용은 special_note 또는 care_items로만 요약한다.
- 날짜는 원문에서 명확하면 ISO 8601 문자열 후보로 작성하고, 불명확하면 null로 둔다.
- 일당은 숫자만 추출한다.
- 간병 요청 이유는 보호자/환자가 왜 간병이 필요한지 한두 문장으로 care_request_reason에 요약한다.
- 문의자 정보는 requester_name, requester_relationship, requester_type, requester_phone에 작성한다.
- requester_relationship은 SELF, SPOUSE, CHILD, PARENT, SIBLING, RELATIVE, LEGAL_GUARDIAN, OTHER, UNKNOWN 중 하나로만 작성한다.
- requester_type은 PATIENT, GUARDIAN, FC, OTHER, UNKNOWN 중 하나로만 작성한다.
- preferred_caregiver_gender은 MALE, FEMALE, ANY 중 하나로만 작성한다.
- mobility_level, dementia_level, toileting_level, meal_assistance_level은 NONE, LOW, MEDIUM, HIGH 중 하나로만 작성한다.
- care_intensity_level은 LOW, MEDIUM, HIGH 중 하나로만 작성한다.
- 반드시 JSON 객체만 반환한다.
"""


class CounselingAnalysisAgent(BaseAgent):
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: genai.Client | None = None


    async def run(self, *, transcript: str, context: dict[str, Any]) -> AgentRunResult:
        """
        Args:
            transcript : 상담 녹취록을 STT로 변환한 원문, context : DB에서 가져온 기존 정보
        """
        if not transcript.strip():
            raise AgentError("STT 원문이 비어 있어 상담 분석을 실행할 수 없습니다.")
        
        # _run_sync()를 별도 스레드에서 실행(FastAPI 요청 처리 흐름은 async 유지, Gemini 호출은 별도 thread에서 blocking 실행)
        output = await asyncio.to_thread(self._run_sync, transcript, context)

        return AgentRunResult(
            summary=output.summary,
            transcript_edited_text=output.transcript_edited_text,
            analysis_result_json={
                "extracted": output.extracted.model_dump(),
                "care_items": [item.model_dump() for item in output.care_items],
                "confidence": output.confidence,
                "missing_fields": output.missing_fields,
                "agent": "CounselingAnalysisAgent",
            },
        )

    def _run_sync(self, transcript: str, context: dict[str, Any]) -> CounselingAnalysisOutput:
        prompt = self._build_prompt(transcript=transcript, context=context)
        response = None
        try:
            response = self._client_or_create().models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=CounselingAnalysisOutput,
                    temperature=0,
                    top_p=0.8,
                    max_output_tokens=self.settings.gemini_max_output_tokens,
                ),
            )

            # LLM이 파싱된 객체를 주면 response.parsed를 검증
            if getattr(response, "parsed", None) is not None:
                return CounselingAnalysisOutput.model_validate(response.parsed)
            
            return CounselingAnalysisOutput.model_validate_json(response.text)
        except ValidationError as exc:
            raise AgentError(f"상담 분석 결과 스키마 검증에 실패했습니다: {exc}") from exc
        except Exception as exc:
            raw_text = getattr(response, "text", None)
            suffix = f" raw={raw_text[:300]}" if raw_text else ""
            raise AgentError(f"Gemini 상담 분석 호출에 실패했습니다: {exc}{suffix}") from exc

    def _build_prompt(self, *, transcript: str, context: dict[str, Any]) -> str:
        return "\n".join(
            [
                "DB_CONTEXT_JSON:",
                json.dumps(context, ensure_ascii=False, default=str),
                "",
                "STT_TRANSCRIPT:",
                transcript,
                "",
                "OUTPUT_REQUIREMENT:",
                "summary, transcript_edited_text, extracted, care_items, confidence, missing_fields를 채운다.",
            ]
        )

    def _client_or_create(self) -> genai.Client:
        if self._client is None:
            if not self.settings.gemini_api_key:
                raise AgentError("GEMINI_API_KEY 또는 GOOGLE_API_KEY가 설정되지 않았습니다.")
            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client
