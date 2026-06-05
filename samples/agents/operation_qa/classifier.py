from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from backend.app.agents.operation_qa.schemas import OperationQAIntent, OperationQAQueryPlan


SEOUL_TIMEZONE = timezone(timedelta(hours=9))

STOPWORDS = {
    "간병사",
    "간병인",
    "요양보호사",
    "환자",
    "보호자",
    "요청",
    "매칭",
    "배정",
    "임시",
    "서비스",
    "일정",
    "문서",
    "운영",
    "지침",
    "상담",
    "내용",
    "정보",
    "요약",
    "알려줘",
    "보여줘",
    "있어",
    "오늘",
    "투입",
    "가능",
    "가능한",
    "누구",
    "누가",
    "있지",
    "있니",
    "있나요",
    "있습니까",
    "있는지",
    "있을까",
    "있을까요",
    "있을지",
    "이번",
    "이번주",
    "데이터화",
    "실패",
    "완료",
    "대기",
}

ROLE_KEYWORDS = {
    "간병사",
    "간병인",
    "요양보호사",
    "환자",
    "보호자",
    "요청",
    "매칭",
    "배정",
    "서비스",
    "일정",
    "문서",
    "운영",
}

KOREAN_PARTICLES = (
    "으로",
    "에게",
    "에서",
    "부터",
    "까지",
    "처럼",
    "보다",
    "하고",
    "이랑",
    "랑",
    "을",
    "를",
    "은",
    "는",
    "이",
    "가",
    "의",
    "와",
    "과",
    "도",
    "만",
)

STOPWORDS.update(
    {
        "간병사",
        "간병사를",
        "간병사는",
        "간병사가",
        "간병사의",
        "간병인",
        "간병인을",
        "간병인은",
        "간병인이",
        "요양보호사",
        "요양보호사를",
        "요양보호사는",
        "요양보호사가",
    }
)


class OperationQAClassifier:
    def build_query_plan(
        self,
        question: str,
        *,
        page_context: str | None = None,
    ) -> OperationQAQueryPlan:
        normalized = question.strip()
        compact = re.sub(r"\s+", "", normalized)
        keyword = self.extract_keyword(normalized)
        filters = self._date_filters(compact)

        if self._is_out_of_scope(compact):
            return OperationQAQueryPlan(route="OUT_OF_SCOPE", intent=OperationQAIntent.OUT_OF_SCOPE)

        if "데이터화" in compact and ("문서" in compact or page_context == "DOCUMENT"):
            status = "FAILED" if "실패" in compact else None
            return OperationQAQueryPlan(
                route="DB",
                intent=OperationQAIntent.OPERATION_DOCUMENT_STATUS,
                keyword=keyword,
                filters={**filters, "datafication_status": status},
                required_tools=["operation_document_tool"],
            )

        if any(token in compact for token in ("지침", "규정", "가이드", "응대", "처리", "어떻게", "금지", "주의", "유의사항")):
            document_type = self.infer_document_type(compact)
            hospital_name = self.extract_hospital_name(normalized)
            is_hybrid = any(token in compact for token in ("정보", "상태", "목록", "보여줘", "조회"))
            return OperationQAQueryPlan(
                route="HYBRID" if is_hybrid else "RAG",
                intent=OperationQAIntent.HYBRID_GUIDE if is_hybrid else OperationQAIntent.OPERATION_DOCUMENT_QA,
                keyword=keyword,
                filters={
                    **filters,
                    "document_type": document_type,
                    "hospital_name": hospital_name,
                },
                required_tools=["operation_document_tool", "rag_tool"] if is_hybrid else ["rag_tool"],
            )

        if "상담" in compact or "녹취" in compact or "통화" in compact:
            return OperationQAQueryPlan(
                route="DB",
                intent=OperationQAIntent.CALL_LOG_SUMMARY,
                keyword=keyword,
                filters=filters,
                required_tools=["call_log_tool"],
            )

        if any(token in compact for token in ("간병사", "간병인", "요양보호사")):
            caregiver_filters: dict[str, Any] = dict(filters)
            if "가능" in compact or "투입" in compact:
                caregiver_filters["availability"] = "available"
                if "오늘" in compact:
                    caregiver_filters["available_date"] = "today"
            return OperationQAQueryPlan(
                route="DB",
                intent=OperationQAIntent.CAREGIVER_SUMMARY,
                keyword=keyword,
                filters=caregiver_filters,
                required_tools=["caregiver_tool"],
            )

        if "환자" in compact:
            return OperationQAQueryPlan(
                route="DB",
                intent=OperationQAIntent.PATIENT_SUMMARY,
                keyword=keyword,
                filters=filters,
                required_tools=["patient_tool"],
            )

        if "FC" in normalized.upper():
            return OperationQAQueryPlan(
                route="DB",
                intent=OperationQAIntent.FC_SUMMARY,
                keyword=keyword,
                filters=filters,
                required_tools=["person_tool"],
            )

        if any(token in compact for token in ("추천완료", "배정대기", "요청", "매칭")):
            request_filters: dict[str, Any] = dict(filters)
            if "추천완료" in compact:
                request_filters["request_status"] = "RECOMMENDED"
                request_filters["without_temporary_assignment"] = True
            elif "배정대기" in compact:
                request_filters["request_status"] = "REQUESTED"
            elif "오늘들어온" in compact:
                request_filters["created_date"] = "today"
            return OperationQAQueryPlan(
                route="DB",
                intent=OperationQAIntent.MATCHING_REQUEST_LIST,
                keyword=keyword,
                filters=request_filters,
                required_tools=["matching_request_tool"],
            )

        if "서비스" in compact or "시작" in compact or "종료" in compact:
            service_filters: dict[str, Any] = dict(filters)
            if "시작" in compact:
                service_filters["status"] = "starts_today" if "오늘" in compact else "starts"
            if "종료" in compact:
                service_filters["status"] = "ends_this_week" if "이번주" in compact else "ends"
            return OperationQAQueryPlan(
                route="DB",
                intent=OperationQAIntent.CARE_SERVICE_STATUS,
                keyword=keyword,
                filters=service_filters,
                required_tools=["care_service_tool"],
            )

        if "일정" in compact:
            return OperationQAQueryPlan(
                route="DB",
                intent=OperationQAIntent.SCHEDULE_LOOKUP,
                keyword=keyword,
                filters=filters,
                required_tools=["schedule_tool"],
            )

        if any(token in compact for token in ("안녕", "도움", "기능", "무엇")):
            return OperationQAQueryPlan(
                route="DB",
                intent=OperationQAIntent.GENERAL_HELP,
                filters=filters,
                required_tools=[],
            )

        return OperationQAQueryPlan(route="OUT_OF_SCOPE", intent=OperationQAIntent.OUT_OF_SCOPE)

    def _clean_keyword(self, value: str | None) -> str | None:
        if not value:
            return None
        keyword = value.strip()
        if not keyword or keyword in STOPWORDS:
            return None
        normalized = keyword
        for particle in KOREAN_PARTICLES:
            if normalized.endswith(particle) and len(normalized) > len(particle) + 1:
                normalized = normalized[: -len(particle)]
                break
        if normalized in STOPWORDS or normalized in ROLE_KEYWORDS:
            return None
        return keyword

    def extract_keyword(self, question: str) -> str | None:
        quoted = re.findall(r"['\"]([^'\"]{2,30})['\"]", question)
        if quoted:
            return self._clean_keyword(quoted[0].strip())

        name_before_role = re.search(r"([가-힣A-Za-z0-9]{2,30})\s*(?:간병사|간병인|요양보호사|환자|FC|보호자)", question)
        if name_before_role:
            candidate = name_before_role.group(1).strip()
            return self._clean_keyword(candidate)

        hospital_name = self.extract_hospital_name(question)
        if hospital_name:
            return hospital_name

        tokens = re.findall(r"[가-힣A-Za-z0-9]{2,30}", question)
        for token in tokens:
            if token not in STOPWORDS and not token.endswith(("해줘", "해주세요")):
                return token
        return None

    def extract_hospital_name(self, question: str) -> str | None:
        match = re.search(r"([가-힣A-Za-z0-9\s]{2,40}?(?:요양\s*병원|병원|의료원|센터))", question)
        if not match:
            return None
        hospital_name = re.sub(r"\s+", " ", match.group(1)).strip()
        hospital_name = re.sub(r"\s+(병원|의료원|센터)$", r"\1", hospital_name)
        return hospital_name

    def infer_document_type(self, compact_question: str) -> str | None:
        if "병원" in compact_question or "요양병원" in compact_question:
            return "HOSPITAL_GUIDE"
        if "센터" in compact_question or "야간" in compact_question or "교체" in compact_question:
            return "CENTER_GUIDE"
        return None

    def _date_filters(self, compact_question: str) -> dict[str, Any]:
        today = datetime.now(SEOUL_TIMEZONE).date()
        if "오늘" in compact_question:
            return {"date": "today", "start_date": today, "end_date": today}
        if "이번주" in compact_question or "이번 주" in compact_question:
            week_end = today + timedelta(days=6 - today.weekday())
            return {"date": "this_week", "start_date": today, "end_date": week_end}
        return {}

    def _is_out_of_scope(self, compact_question: str) -> bool:
        blocked = ("진단", "처방", "법률자문", "투자", "날씨", "뉴스")
        return any(token in compact_question for token in blocked)
