from __future__ import annotations

import asyncio
import json
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentError
from backend.app.agents.operation_qa.classifier import OperationQAClassifier
from backend.app.agents.operation_qa.privacy import sanitize_answer, sanitize_for_llm
from backend.app.agents.operation_qa.rag import OperationQARagTool
from backend.app.agents.operation_qa.schemas import (
    OperationQAEvidence,
    OperationQAIntent,
    OperationQAQueryPlan,
    OperationQAResult,
)
from backend.app.agents.operation_qa.tools import OperationQATools
from backend.app.core.config import get_settings


SYSTEM_INSTRUCTION = """
당신은 DUSON 관리자용 운영 도우미 챗봇입니다.

응답 원칙:
- 제공된 DB 조회 결과와 운영 문서 근거만 사용합니다.
- 의료 판단, 법률 판단, 확정적 지시는 하지 않습니다.
- 근거가 부족하면 추측하지 말고 "확인 필요"라고 말합니다.
- 운영자가 바로 읽을 수 있도록 한국어로 짧고 명확하게 답합니다.
- 개인정보와 민감정보는 불필요하게 노출하지 않습니다.
"""


class OperationQAAgent:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.classifier = OperationQAClassifier()
        self.db_tools = OperationQATools(session)
        self.rag_tool = OperationQARagTool(session)
        self._client: genai.Client | None = None

    async def run(
        self,
        *,
        question: str,
        page_context: str | None,
        recent_messages: list[dict[str, str]] | None = None,
    ) -> OperationQAResult:
        normalized = question.strip()
        if not normalized:
            raise AgentError("질문을 입력해 주세요.")

        plan = self.classifier.build_query_plan(normalized, page_context=page_context)
        if plan.route == "OUT_OF_SCOPE":
            answer = (
                "현재 챗봇은 간병 운영 데이터, 일정, 매칭 상태, 운영 문서 지침 범위의 "
                "조회성 질문만 답할 수 있습니다. 해당 내용은 담당자 확인이 필요합니다."
            )
            return OperationQAResult(answer=answer, route=plan.route, intent=plan.intent)

        evidence = await self._collect_evidence(normalized, plan)
        safe_evidence = OperationQAEvidence(
            data=sanitize_for_llm(evidence.data),
            sources=evidence.sources,
            warnings=evidence.warnings,
        )
        answer = await self._compose_answer(
            question=normalized,
            page_context=page_context,
            plan=plan,
            evidence=safe_evidence,
            recent_messages=recent_messages or [],
        )
        return OperationQAResult(
            answer=sanitize_answer(answer),
            route=plan.route,
            intent=plan.intent,
            sources=[source.to_dict() for source in safe_evidence.sources],
            warnings=safe_evidence.warnings,
            related_actions=[],
        )

    async def _collect_evidence(self, question: str, plan: OperationQAQueryPlan) -> OperationQAEvidence:
        evidence = OperationQAEvidence(data={})
        if plan.route in {"DB", "HYBRID"}:
            evidence = evidence.merge(await self.db_tools.collect(plan))
        if plan.route in {"RAG", "HYBRID"}:
            evidence = evidence.merge(await self.rag_tool.lookup(question, plan))
        return evidence

    async def _compose_answer(
        self,
        *,
        question: str,
        page_context: str | None,
        plan: OperationQAQueryPlan,
        evidence: OperationQAEvidence,
        recent_messages: list[dict[str, str]],
    ) -> str:
        prompt = {
            "question": question,
            "page_context": page_context,
            "route": plan.route,
            "intent": plan.intent.value,
            "filters": sanitize_for_llm(plan.filters),
            "evidence": evidence.data,
            "sources": [source.to_dict() for source in evidence.sources],
            "warnings": evidence.warnings,
            "recent_messages": recent_messages[-6:],
            "answer_format": self._answer_format(plan.intent),
        }
        try:
            return await asyncio.to_thread(self._generate_answer_sync, prompt)
        except Exception:
            return self._fallback_answer(plan=plan, evidence=evidence)

    def _generate_answer_sync(self, prompt: dict[str, Any]) -> str:
        response = self._client_or_create().models.generate_content(
            model=self.settings.gemini_model,
            contents=json.dumps(prompt, ensure_ascii=False, default=str),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.1,
                top_p=0.8,
                max_output_tokens=min(self.settings.gemini_max_output_tokens, 900),
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise AgentError("Gemini 응답이 비어 있습니다.")
        return text

    def _client_or_create(self) -> genai.Client:
        if self._client is None:
            if self.settings.gemini_api_key:
                self._client = genai.Client(api_key=self.settings.gemini_api_key)
            else:
                self._client = genai.Client()
        return self._client

    def _answer_format(self, intent: OperationQAIntent) -> str:
        if intent in {OperationQAIntent.OPERATION_DOCUMENT_QA, OperationQAIntent.HYBRID_GUIDE}:
            return "확인된 지침, 운영 적용 방법, 주의할 점, 근거 문서, 확인 필요 사항 순서로 짧게 답합니다."
        return "한국어 3~6문장으로 답하고, 목록이 필요한 경우 짧은 bullet로 정리합니다."

    def _fallback_answer(self, *, plan: OperationQAQueryPlan, evidence: OperationQAEvidence) -> str:
        if evidence.warnings and not evidence.sources:
            return " ".join(evidence.warnings)

        data = evidence.data
        if plan.intent == OperationQAIntent.MATCHING_REQUEST_LIST:
            count = data.get("matching_request_count", 0)
            items = data.get("matching_requests") or []
            if not items:
                return "조건에 맞는 매칭 요청을 찾지 못했습니다. 상태나 날짜 조건 확인이 필요합니다."
            return f"조건에 맞는 매칭 요청은 {count}건입니다. 주요 항목: {self._brief_items(items, 'matching_request_id', 'patient_name_snapshot')}"

        if plan.intent == OperationQAIntent.CAREGIVER_SUMMARY:
            items = data.get("caregivers") or []
            if not items:
                return "조건에 맞는 간병사를 찾지 못했습니다."
            if data.get("availability_basis") == "caregiver_status_ACTIVE":
                return (
                    f"현재 등록 상태 기준으로 투입 가능 후보 간병사는 {len(items)}건입니다. "
                    f"{self._brief_items(items, 'caregiver_id', 'name')} "
                    "실제 투입 가능 여부는 일정 중복과 담당자 확인이 필요합니다."
                )
            return f"간병사 조회 결과는 {len(items)}건입니다. {self._brief_items(items, 'caregiver_id', 'name')}"

        if plan.intent == OperationQAIntent.PATIENT_SUMMARY:
            items = data.get("patients") or []
            if not items:
                return "조건에 맞는 환자를 찾지 못했습니다."
            return f"환자 조회 결과는 {len(items)}건입니다. {self._brief_items(items, 'patient_id', 'name')}"

        if plan.intent == OperationQAIntent.CARE_SERVICE_STATUS:
            count = data.get("care_service_count", 0)
            items = data.get("care_services") or []
            return f"조건에 맞는 서비스는 {count}건입니다. {self._brief_items(items, 'care_service_id', 'patient_name')}" if items else "조건에 맞는 서비스 일정을 찾지 못했습니다."

        if plan.intent == OperationQAIntent.SCHEDULE_LOOKUP:
            count = data.get("schedule_count", 0)
            items = data.get("schedules") or []
            return f"조건에 맞는 일정은 {count}건입니다. {self._brief_items(items, 'schedule_id', 'title')}" if items else "조건에 맞는 일정이 없습니다."

        if plan.intent == OperationQAIntent.OPERATION_DOCUMENT_STATUS:
            count = data.get("operation_document_count", 0)
            items = data.get("operation_documents") or []
            return f"조건에 맞는 운영 문서는 {count}건입니다. {self._brief_items(items, 'operation_document_id', 'title')}" if items else "조건에 맞는 운영 문서가 없습니다."

        rag_chunks = data.get("rag_chunks") or []
        if rag_chunks:
            top = rag_chunks[0]
            return (
                f"운영 문서 기준으로 가장 가까운 근거는 '{top.get('title')}'입니다. "
                f"{self._shorten(top.get('chunk_text'), 220)} "
                "세부 적용은 최신 문서와 담당자 확인이 필요합니다."
            )

        if data.get("help"):
            return "가능한 질문은 매칭 요청, 간병사/환자 정보, 서비스 일정, 운영 문서 상태와 지침 조회입니다."

        return "확인 가능한 DB 또는 운영 문서 근거가 부족합니다. 담당자 확인이 필요합니다."

    def _brief_items(self, items: list[dict[str, Any]], id_key: str, label_key: str) -> str:
        values = []
        for item in items[:3]:
            label = item.get(label_key) or "이름 없음"
            values.append(f"#{item.get(id_key)} {label}")
        suffix = " 외" if len(items) > 3 else ""
        return ", ".join(values) + suffix

    def _shorten(self, text: Any, limit: int) -> str:
        value = str(text or "").strip().replace("\n", " ")
        if len(value) <= limit:
            return value
        return f"{value[:limit].rstrip()}..."
