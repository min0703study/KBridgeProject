from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from typing import Iterable
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import case, delete, func, literal, or_, select

from backend.app.agents.base import AgentError
from backend.app.core.config import get_settings
from backend.app.db.models import (
    CareService,
    CareServiceLink,
    CaregiverProfile,
    CaregiverTag,
    Contract,
    Hospital,
    MatchingRecommendation,
    MatchingRequest,
    MatchingRequestRequirement,
    PatientProfile,
    Person,
    Review,
    Schedule,
    TemporaryAssignment,
)
from backend.app.repositories.matching import MatchingRepository
from backend.app.schemas.calls import CallLogRead
from backend.app.schemas.matching import MatchingCompletionRead, MatchingRecommendationRead, MatchingRequestRead


class MatchingRecommendationError(AgentError):
    pass


class MatchingRequestNotFoundError(MatchingRecommendationError):
    pass


class MatchingRequestNotRunnableError(MatchingRecommendationError):
    pass


class NoEligibleCandidatesError(MatchingRecommendationError):
    pass


class MatchingRecommendationLLMError(MatchingRecommendationError):
    pass


class PersonBrief(BaseModel):
    person_id: int | None = None
    name: str | None = None
    gender: str | None = None
    phone: str | None = None
    birth_date: str | None = None
    profile_image_url: str | None = None


class MatchingRequirementContext(BaseModel):
    disease_note: str | None = None
    allergy_note: str | None = None
    mobility_level: str | None = None
    dementia_level: str | None = None
    toileting_level: str | None = None
    meal_assistance_level: str | None = None
    medication_required: bool = False
    rehab_required: bool = False
    suction_required: bool = False
    night_care_required: bool = False
    infection_precaution_required: bool = False
    preferred_caregiver_gender: str | None = None
    care_intensity_level: str | None = None
    preferred_conditions_json: dict[str, Any] | None = None
    care_instruction_json: dict[str, Any] | None = None
    special_note: str | None = None


class MatchingRequestContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    matching_request_id: int
    request_status: str
    care_location_type: str
    proposed_start_datetime: datetime
    proposed_end_datetime: datetime | None = None
    proposed_daily_wage: Decimal | None = None
    care_request_reason: str | None = None
    hospital_id: int | None = None
    hospital_name: str | None = None
    hospital_room: str | None = None
    request_memo: str | None = None
    patient_id: int | None = None
    patient_name: str | None = None
    patient_gender: str | None = None
    patient_birth_date: str | None = None
    requester_name: str | None = None
    requester_relationship: str | None = None
    requester_type: str | None = None
    requirement: MatchingRequirementContext | None = None


class CaregiverCandidate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    caregiver_id: int
    person: PersonBrief
    person_is_active: bool = True
    member_number: str
    caregiver_status: str
    registered_at: str | None = None
    average_rating: Decimal = Decimal("0")
    rating_count: int = 0
    specialties: str | None = None
    tags: list[str] = Field(default_factory=list)
    has_contract_conflict: bool = False
    has_care_service_conflict: bool = False
    has_temporary_assignment_conflict: bool = False
    has_schedule_conflict: bool = False


class ExcludedCandidate(BaseModel):
    caregiver_id: int
    caregiver_name: str | None = None
    reasons: list[str]


class HardFilterResult(BaseModel):
    eligible_candidates: list[CaregiverCandidate]
    excluded_candidates: list[ExcludedCandidate]
    summary: dict[str, Any]


class CandidateHistoryMetrics(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    caregiver_id: int
    total_contract_count: int = 0
    same_hospital_contract_count: int = 0
    average_daily_wage: Decimal | None = None
    review_count: int = 0
    average_ai_score: Decimal | None = None


class CandidateScoreBreakdown(BaseModel):
    care_fit: float = 0
    hospital_experience: float = 0
    rating: float = 0
    tag_fit: float = 0
    schedule_stability: float = 0
    wage_fit: float = 0
    operation_risk: float = 0


class ScoredCaregiverCandidate(BaseModel):
    caregiver_id: int
    caregiver_name: str | None = None
    total_score: float
    score_breakdown: CandidateScoreBreakdown
    candidate: dict[str, Any]
    history_metrics: CandidateHistoryMetrics
    score_reason_tags: list[str] = Field(default_factory=list)
    score_warning_tags: list[str] = Field(default_factory=list)


class RecommendationReason(BaseModel):
    summary: str
    matched_points: list[str] = Field(default_factory=list)
    risk_points: list[str] = Field(default_factory=list)
    score_adjustment_reason: str | None = None


class RerankedCaregiver(BaseModel):
    caregiver_id: int
    rank: int = Field(ge=1, le=3)
    final_score: float = Field(ge=0, le=100)
    reason: RecommendationReason


class RerankResult(BaseModel):
    recommendations: list[RerankedCaregiver] = Field(default_factory=list, max_length=3)


class FinalRecommendation(BaseModel):
    caregiver_id: int
    recommendation_rank: int = Field(ge=1, le=3)
    match_score: float = Field(ge=0, le=100)
    recommendation_reason_json: dict[str, Any]
    caregiver_snapshot_json: dict[str, Any]


LEVEL_WEIGHT = {
    None: 0,
    "NONE": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
}

CARE_KEYWORDS = {
    "mobility": ["mobility", "walking", "transfer", "rehab", "거동", "이동", "보행", "침상", "재활"],
    "dementia": ["dementia", "cognitive", "치매", "인지", "섬망"],
    "toileting": ["toileting", "diaper", "배변", "배뇨", "기저귀", "화장실"],
    "meal": ["meal", "feeding", "식사", "식이", "경관", "연하"],
    "medication": ["medication", "medicine", "복약", "투약", "약"],
    "rehab": ["rehab", "exercise", "재활", "운동", "물리치료"],
    "suction": ["suction", "석션", "흡인"],
    "night": ["night", "overnight", "야간", "밤", "수면"],
    "infection": ["infection", "isolation", "감염", "격리", "주의"],
    "allergy": ["allergy", "알레르기", "알러지"],
}

KOREAN_CARE_LABEL = {
    "mobility": "이동 보조",
    "dementia": "인지 돌봄",
    "toileting": "배변 보조",
    "meal assistance": "식사 보조",
    "medication": "복약 보조",
    "rehab": "재활 보조",
    "night care": "야간 간병",
    "infection precaution": "감염 주의",
}

KOREAN_LEVEL_LABEL = {
    "LOW": "낮음",
    "MEDIUM": "보통",
    "HIGH": "높음",
}

KOREAN_KEYWORD_LABEL = {
    "mobility": "이동 보조",
    "walking": "보행",
    "transfer": "이동",
    "rehab": "재활",
    "dementia": "인지 돌봄",
    "cognitive": "인지 돌봄",
    "toileting": "배변 보조",
    "diaper": "기저귀",
    "meal": "식사 보조",
    "feeding": "식사 보조",
    "medication": "복약 보조",
    "medicine": "복약",
    "suction": "석션",
    "night": "야간 간병",
    "overnight": "야간 간병",
    "infection": "감염 주의",
    "isolation": "격리",
    "allergy": "알레르기",
}


def hard_filter_caregivers(
    *,
    request_context: MatchingRequestContext,
    candidates: list[CaregiverCandidate],
) -> HardFilterResult:
    eligible_candidates: list[CaregiverCandidate] = []
    excluded_candidates: list[ExcludedCandidate] = []
    preferred_gender = request_context.requirement.preferred_caregiver_gender if request_context.requirement else None

    for candidate in candidates:
        reasons: list[str] = []

        if candidate.caregiver_status != "ACTIVE":
            reasons.append(f"caregiver status is not ACTIVE: {candidate.caregiver_status}")
        if not candidate.person_is_active:
            reasons.append("person is inactive")
        if (
            preferred_gender
            and preferred_gender != "ANY"
            and candidate.person.gender
            and candidate.person.gender != preferred_gender
        ):
            reasons.append(f"preferred caregiver gender mismatch: request={preferred_gender}, candidate={candidate.person.gender}")
        if candidate.has_contract_conflict:
            reasons.append("contract schedule conflict")
        if candidate.has_care_service_conflict:
            reasons.append("care service schedule conflict")
        if candidate.has_temporary_assignment_conflict:
            reasons.append("temporary assignment schedule conflict")
        if candidate.has_schedule_conflict:
            reasons.append("personal schedule conflict")

        if reasons:
            excluded_candidates.append(
                ExcludedCandidate(
                    caregiver_id=candidate.caregiver_id,
                    caregiver_name=candidate.person.name,
                    reasons=reasons,
                )
            )
        else:
            eligible_candidates.append(candidate)

    reason_counts: dict[str, int] = {}
    for excluded in excluded_candidates:
        for reason in excluded.reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return HardFilterResult(
        eligible_candidates=eligible_candidates,
        excluded_candidates=excluded_candidates,
        summary={
            "total_candidates": len(candidates),
            "eligible_count": len(eligible_candidates),
            "excluded_count": len(excluded_candidates),
            "excluded_reason_counts": reason_counts,
        },
    )


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _candidate_text(candidate: CaregiverCandidate) -> str:
    return " ".join([candidate.specialties or "", *candidate.tags]).lower()


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    lower_text = text.lower()
    return any(keyword.lower() in lower_text for keyword in keywords)


def _score_level_need(*, level: str | None, candidate_text: str, keywords: list[str]) -> float:
    normalized = level or "NONE"
    if normalized == "NONE":
        return 4.0
    has_keyword = _contains_any(candidate_text, keywords)
    if normalized == "LOW":
        return 4.0 if has_keyword else 3.0
    if normalized == "MEDIUM":
        return 4.0 if has_keyword else 1.5
    if normalized == "HIGH":
        return 4.0 if has_keyword else 0.5
    return 2.0


def _score_boolean_need(*, required: bool, candidate_text: str, keywords: list[str], max_score: float) -> float:
    if not required:
        return max_score
    return max_score if _contains_any(candidate_text, keywords) else max_score * 0.25


def _score_care_fit(request_context: MatchingRequestContext, candidate: CaregiverCandidate) -> tuple[float, list[str], list[str]]:
    requirement = request_context.requirement
    text = _candidate_text(candidate)
    if requirement is None:
        return 18.0, ["No detailed care requirement; neutral score applied"], ["Detailed care requirement is missing"]

    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []
    level_items = [
        ("mobility", requirement.mobility_level, CARE_KEYWORDS["mobility"]),
        ("dementia", requirement.dementia_level, CARE_KEYWORDS["dementia"]),
        ("toileting", requirement.toileting_level, CARE_KEYWORDS["toileting"]),
        ("meal assistance", requirement.meal_assistance_level, CARE_KEYWORDS["meal"]),
    ]
    for label, level, keywords in level_items:
        item_score = _score_level_need(level=level, candidate_text=text, keywords=keywords)
        score += item_score
        if level in {"MEDIUM", "HIGH"}:
            if item_score >= 4:
                reasons.append(f"{label} {level} requirement matches caregiver tags or specialties")
            else:
                warnings.append(f"{label} {level} requirement has weak tag or specialty evidence")

    boolean_items = [
        ("medication", requirement.medication_required, CARE_KEYWORDS["medication"]),
        ("rehab", requirement.rehab_required, CARE_KEYWORDS["rehab"]),
        ("suction", requirement.suction_required, CARE_KEYWORDS["suction"]),
        ("night care", requirement.night_care_required, CARE_KEYWORDS["night"]),
        ("infection precaution", requirement.infection_precaution_required, CARE_KEYWORDS["infection"]),
    ]
    each_boolean_max = 14.0 / len(boolean_items)
    for label, required, keywords in boolean_items:
        item_score = _score_boolean_need(
            required=required,
            candidate_text=text,
            keywords=keywords,
            max_score=each_boolean_max,
        )
        score += item_score
        if required:
            if item_score >= each_boolean_max:
                reasons.append(f"{label} requirement matches caregiver tags or specialties")
            else:
                warnings.append(f"{label} requirement has weak tag or specialty evidence")

    return min(round(score, 2), 30.0), reasons, warnings


def _score_hospital_experience(metrics: CandidateHistoryMetrics) -> tuple[float, list[str]]:
    same = metrics.same_hospital_contract_count
    total = metrics.total_contract_count
    if same >= 3:
        return 15.0, [f"same hospital contract history: {same} cases"]
    if same >= 1:
        return 11.0, [f"same hospital contract history: {same} cases"]
    if total >= 5:
        return 8.0, [f"overall contract history: {total} cases"]
    if total >= 1:
        return 5.0, [f"overall contract history: {total} cases"]
    return 3.0, ["limited contract history"]


def _score_rating(candidate: CaregiverCandidate, metrics: CandidateHistoryMetrics) -> tuple[float, list[str], list[str]]:
    average_rating = _to_float(candidate.average_rating)
    rating_count = candidate.rating_count or 0
    if average_rating <= 0 and metrics.average_ai_score is None:
        return 10.0, ["rating data is limited; neutral score applied"], ["rating data is limited"]

    profile_rating_score = min(average_rating / 5.0, 1.0) * 14.0
    confidence_score = min(rating_count, 10) / 10.0 * 4.0
    ai_review_score = min(_to_float(metrics.average_ai_score) / 5.0, 1.0) * 2.0 if metrics.average_ai_score is not None else 1.0
    score = profile_rating_score + confidence_score + ai_review_score
    reasons: list[str] = []
    warnings: list[str] = []
    if rating_count >= 5:
        reasons.append(f"rating {average_rating:.2f} from {rating_count} reviews")
    else:
        warnings.append(f"low review count: {rating_count}")
    if metrics.average_ai_score is not None:
        reasons.append(f"average review AI score {float(metrics.average_ai_score):.2f}")
    return min(round(score, 2), 20.0), reasons, warnings


def _build_requested_keywords(request_context: MatchingRequestContext) -> list[str]:
    requirement = request_context.requirement
    if requirement is None:
        return []
    keywords: list[str] = []
    for level, level_keywords in [
        (requirement.mobility_level, CARE_KEYWORDS["mobility"]),
        (requirement.dementia_level, CARE_KEYWORDS["dementia"]),
        (requirement.toileting_level, CARE_KEYWORDS["toileting"]),
        (requirement.meal_assistance_level, CARE_KEYWORDS["meal"]),
    ]:
        if LEVEL_WEIGHT.get(level, 0) >= 2:
            keywords.extend(level_keywords)
    for required, boolean_keywords in [
        (requirement.medication_required, CARE_KEYWORDS["medication"]),
        (requirement.rehab_required, CARE_KEYWORDS["rehab"]),
        (requirement.suction_required, CARE_KEYWORDS["suction"]),
        (requirement.night_care_required, CARE_KEYWORDS["night"]),
        (requirement.infection_precaution_required, CARE_KEYWORDS["infection"]),
    ]:
        if required:
            keywords.extend(boolean_keywords)
    if requirement.allergy_note:
        keywords.extend(CARE_KEYWORDS["allergy"])
    return sorted(set(keywords))


def _score_tag_fit(request_context: MatchingRequestContext, candidate: CaregiverCandidate) -> tuple[float, list[str], list[str]]:
    requested_keywords = _build_requested_keywords(request_context)
    candidate_text = _candidate_text(candidate)
    if not requested_keywords:
        return 10.0, ["no high-priority requested tags; neutral score applied"], []
    matched_keywords = [keyword for keyword in requested_keywords if keyword.lower() in candidate_text]
    match_ratio = len(matched_keywords) / len(requested_keywords)
    score = 5.0 + match_ratio * 10.0
    if matched_keywords:
        return round(min(score, 15.0), 2), [f"matched requested keywords: {', '.join(matched_keywords[:5])}"], []
    return round(min(score, 15.0), 2), [], ["no direct tag or specialty match for requested keywords"]


def _score_schedule_stability(candidate: CaregiverCandidate) -> tuple[float, list[str]]:
    if any(
        [
            candidate.has_contract_conflict,
            candidate.has_care_service_conflict,
            candidate.has_temporary_assignment_conflict,
            candidate.has_schedule_conflict,
        ]
    ):
        return 0.0, ["schedule conflict flag exists"]
    return 10.0, ["no schedule conflict in requested period"]


def _score_wage_fit(request_context: MatchingRequestContext, metrics: CandidateHistoryMetrics) -> tuple[float, list[str], list[str]]:
    proposed_daily_wage = request_context.proposed_daily_wage
    average_daily_wage = metrics.average_daily_wage
    if proposed_daily_wage is None or average_daily_wage is None:
        return 3.0, ["daily wage comparison data is limited; neutral score applied"], []
    proposed = _to_float(proposed_daily_wage)
    average = _to_float(average_daily_wage)
    if proposed <= 0 or average <= 0:
        return 3.0, ["daily wage comparison data is limited; neutral score applied"], []
    ratio = average / proposed
    if ratio <= 1.0:
        return 5.0, [f"historical average wage is within proposed wage: {average:.0f}"], []
    if ratio <= 1.1:
        return 4.0, [f"historical average wage is close to proposed wage: {average:.0f}"], []
    if ratio <= 1.2:
        return 2.0, [], [f"historical average wage is above proposed wage: {average:.0f}"]
    return 0.0, [], [f"historical average wage is much above proposed wage: {average:.0f}"]


def _score_operation_risk(candidate: CaregiverCandidate) -> tuple[float, list[str], list[str]]:
    average_rating = _to_float(candidate.average_rating)
    rating_count = candidate.rating_count or 0
    if rating_count >= 3 and average_rating < 3.5:
        return 2.0, [], [f"low average rating: {average_rating:.2f}"]
    return 5.0, ["no obvious operation risk flags"], []


def calculate_candidate_score(
    *,
    request_context: MatchingRequestContext,
    candidate: CaregiverCandidate,
    metrics: CandidateHistoryMetrics,
) -> ScoredCaregiverCandidate:
    care_fit, care_reasons, care_warnings = _score_care_fit(request_context, candidate)
    hospital_score, hospital_reasons = _score_hospital_experience(metrics)
    rating_score, rating_reasons, rating_warnings = _score_rating(candidate, metrics)
    tag_score, tag_reasons, tag_warnings = _score_tag_fit(request_context, candidate)
    schedule_score, schedule_reasons = _score_schedule_stability(candidate)
    wage_score, wage_reasons, wage_warnings = _score_wage_fit(request_context, metrics)
    risk_score, risk_reasons, risk_warnings = _score_operation_risk(candidate)

    breakdown = CandidateScoreBreakdown(
        care_fit=care_fit,
        hospital_experience=hospital_score,
        rating=rating_score,
        tag_fit=tag_score,
        schedule_stability=schedule_score,
        wage_fit=wage_score,
        operation_risk=risk_score,
    )
    total_score = round(sum(breakdown.model_dump().values()), 2)
    return ScoredCaregiverCandidate(
        caregiver_id=candidate.caregiver_id,
        caregiver_name=candidate.person.name,
        total_score=total_score,
        score_breakdown=breakdown,
        candidate=candidate.model_dump(mode="json"),
        history_metrics=metrics,
        score_reason_tags=[
            *care_reasons,
            *hospital_reasons,
            *rating_reasons,
            *tag_reasons,
            *schedule_reasons,
            *wage_reasons,
            *risk_reasons,
        ],
        score_warning_tags=[*care_warnings, *rating_warnings, *tag_warnings, *wage_warnings, *risk_warnings],
    )


def score_candidates_for_request(
    *,
    request_context: MatchingRequestContext,
    candidates: list[CaregiverCandidate],
    metrics_by_caregiver_id: dict[int, CandidateHistoryMetrics],
    limit: int = 20,
) -> list[ScoredCaregiverCandidate]:
    scored_candidates = [
        calculate_candidate_score(
            request_context=request_context,
            candidate=candidate,
            metrics=metrics_by_caregiver_id.get(
                candidate.caregiver_id,
                CandidateHistoryMetrics(caregiver_id=candidate.caregiver_id),
            ),
        )
        for candidate in candidates
    ]
    scored_candidates.sort(key=lambda item: item.total_score, reverse=True)
    return scored_candidates[:limit]


def validate_rerank_result(
    *,
    rerank_result: RerankResult,
    scored_candidates: list[ScoredCaregiverCandidate],
) -> None:
    candidate_ids = {candidate.caregiver_id for candidate in scored_candidates}
    recommendations = rerank_result.recommendations
    if not recommendations:
        raise MatchingRecommendationLLMError("Gemini did not return any recommendations.")
    if len(recommendations) > 3:
        raise MatchingRecommendationLLMError("Gemini returned more than 3 recommendations.")

    seen_caregiver_ids: set[int] = set()
    seen_ranks: set[int] = set()
    for item in recommendations:
        if item.caregiver_id not in candidate_ids:
            raise MatchingRecommendationLLMError(f"Gemini returned an unknown caregiver_id: {item.caregiver_id}")
        if item.caregiver_id in seen_caregiver_ids:
            raise MatchingRecommendationLLMError(f"Gemini returned a duplicate caregiver_id: {item.caregiver_id}")
        if item.rank in seen_ranks:
            raise MatchingRecommendationLLMError(f"Gemini returned a duplicate rank: {item.rank}")
        seen_caregiver_ids.add(item.caregiver_id)
        seen_ranks.add(item.rank)

    expected_ranks = set(range(1, len(recommendations) + 1))
    if seen_ranks != expected_ranks:
        raise MatchingRecommendationLLMError(f"Gemini ranks must start at 1 and be continuous: {sorted(seen_ranks)}")


def _has_english_word(value: str | None) -> bool:
    return bool(value and re.search(r"[A-Za-z]{2,}", value))


def _koreanize_keywords(value: str) -> str:
    labels: list[str] = []
    for item in re.split(r"[,/|]\s*", value):
        cleaned = item.strip()
        if not cleaned:
            continue
        labels.append(KOREAN_KEYWORD_LABEL.get(cleaned.lower(), cleaned))
    return ", ".join(dict.fromkeys(labels))


def _koreanize_rule_text(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None

    direct_map = {
        "No detailed care requirement; neutral score applied": "상세 돌봄 조건이 없어 중립 점수를 적용했습니다.",
        "Detailed care requirement is missing": "상세 돌봄 조건이 입력되지 않았습니다.",
        "limited contract history": "계약 이력이 많지 않습니다.",
        "rating data is limited; neutral score applied": "평점 데이터가 부족해 중립 점수를 적용했습니다.",
        "rating data is limited": "평점 데이터가 부족합니다.",
        "no high-priority requested tags; neutral score applied": "우선 확인할 요청 태그가 없어 중립 점수를 적용했습니다.",
        "no direct tag or specialty match for requested keywords": "요청 조건과 직접 일치하는 태그나 전문 분야 근거가 부족합니다.",
        "schedule conflict flag exists": "요청 기간에 일정 충돌 가능성이 있습니다.",
        "no schedule conflict in requested period": "요청 기간에 확인된 일정 충돌이 없습니다.",
        "daily wage comparison data is limited; neutral score applied": "일급 비교 데이터가 부족해 중립 점수를 적용했습니다.",
        "no obvious operation risk flags": "뚜렷한 운영 리스크가 확인되지 않았습니다.",
    }
    if text in direct_map:
        return direct_map[text]

    match = re.fullmatch(r"(.+) (LOW|MEDIUM|HIGH) requirement matches caregiver tags or specialties", text)
    if match:
        label = KOREAN_CARE_LABEL.get(match.group(1), match.group(1))
        level = KOREAN_LEVEL_LABEL.get(match.group(2), match.group(2))
        return f"{label} 요구 수준({level})과 간병사 태그 또는 전문 분야가 잘 맞습니다."

    match = re.fullmatch(r"(.+) (LOW|MEDIUM|HIGH) requirement has weak tag or specialty evidence", text)
    if match:
        label = KOREAN_CARE_LABEL.get(match.group(1), match.group(1))
        level = KOREAN_LEVEL_LABEL.get(match.group(2), match.group(2))
        return f"{label} 요구 수준({level})에 대한 태그 또는 전문 분야 근거가 부족합니다."

    match = re.fullmatch(r"(.+) requirement matches caregiver tags or specialties", text)
    if match:
        label = KOREAN_CARE_LABEL.get(match.group(1), match.group(1))
        return f"{label} 요구 조건과 간병사 태그 또는 전문 분야가 잘 맞습니다."

    match = re.fullmatch(r"(.+) requirement has weak tag or specialty evidence", text)
    if match:
        label = KOREAN_CARE_LABEL.get(match.group(1), match.group(1))
        return f"{label} 요구 조건에 대한 태그 또는 전문 분야 근거가 부족합니다."

    match = re.fullmatch(r"same hospital contract history: (\d+) cases", text)
    if match:
        return f"동일 병원 계약 이력이 {match.group(1)}건 있습니다."

    match = re.fullmatch(r"overall contract history: (\d+) cases", text)
    if match:
        return f"전체 계약 이력이 {match.group(1)}건 있습니다."

    match = re.fullmatch(r"rating ([\d.]+) from (\d+) reviews", text)
    if match:
        return f"후기 {match.group(2)}건 기준 평균 평점이 {match.group(1)}점입니다."

    match = re.fullmatch(r"average review AI score ([\d.]+)", text)
    if match:
        return f"후기 자동 평가 평균 점수는 {match.group(1)}점입니다."

    match = re.fullmatch(r"low review count: (\d+)", text)
    if match:
        return f"후기 수가 {match.group(1)}건으로 적습니다."

    match = re.fullmatch(r"matched requested keywords: (.+)", text)
    if match:
        return f"요청 조건 키워드와 일치합니다: {_koreanize_keywords(match.group(1))}"

    match = re.fullmatch(r"historical average wage is within proposed wage: ([\d.]+)", text)
    if match:
        return f"기존 평균 일급이 제안 일급 범위 안에 있습니다: {float(match.group(1)):,.0f}원"

    match = re.fullmatch(r"historical average wage is close to proposed wage: ([\d.]+)", text)
    if match:
        return f"기존 평균 일급이 제안 일급과 비슷합니다: {float(match.group(1)):,.0f}원"

    match = re.fullmatch(r"historical average wage is above proposed wage: ([\d.]+)", text)
    if match:
        return f"기존 평균 일급이 제안 일급보다 높습니다: {float(match.group(1)):,.0f}원"

    match = re.fullmatch(r"historical average wage is much above proposed wage: ([\d.]+)", text)
    if match:
        return f"기존 평균 일급이 제안 일급보다 많이 높습니다: {float(match.group(1)):,.0f}원"

    match = re.fullmatch(r"low average rating: ([\d.]+)", text)
    if match:
        return f"평균 평점이 낮은 편입니다: {match.group(1)}점"

    return None if _has_english_word(text) else text


def _koreanize_text_list(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        korean = _koreanize_rule_text(value)
        if korean and korean not in result:
            result.append(korean)
    return result


def _safe_korean_text(value: str | None, fallback: str) -> str:
    translated = _koreanize_rule_text(value)
    if translated and not _has_english_word(translated):
        return translated
    return fallback


def _safe_korean_caregiver_name(value: str | None) -> str:
    if value and not _has_english_word(value):
        return value
    return "해당 간병사"


def _build_korean_reason_json(
    *,
    reranked: RerankedCaregiver,
    original_candidate: ScoredCaregiverCandidate,
) -> dict[str, Any]:
    caregiver_name = _safe_korean_caregiver_name(original_candidate.caregiver_name)
    fallback_summary = f"{caregiver_name}님은 요청 조건과 운영 점수 기준에서 상위 후보로 추천됩니다."
    matched_points = [
        _safe_korean_text(item, "")
        for item in reranked.reason.matched_points
        if _safe_korean_text(item, "")
    ]
    if not matched_points or any(_has_english_word(item) for item in matched_points):
        matched_points = _koreanize_text_list(original_candidate.score_reason_tags)
    risk_points = [
        _safe_korean_text(item, "")
        for item in reranked.reason.risk_points
        if _safe_korean_text(item, "")
    ]
    if not risk_points or any(_has_english_word(item) for item in risk_points):
        risk_points = _koreanize_text_list(original_candidate.score_warning_tags)

    return {
        "summary": _safe_korean_text(reranked.reason.summary, fallback_summary),
        "matched_points": matched_points,
        "risk_points": risk_points,
        "score_adjustment_reason": _safe_korean_text(
            reranked.reason.score_adjustment_reason,
            "규칙 점수와 후보 이력을 기준으로 최종 순위를 조정했습니다.",
        )
        if reranked.reason.score_adjustment_reason
        else None,
        "rule_total_score": original_candidate.total_score,
        "score_breakdown": original_candidate.score_breakdown.model_dump(mode="json"),
        "rule_reason_tags": _koreanize_text_list(original_candidate.score_reason_tags),
        "rule_warning_tags": _koreanize_text_list(original_candidate.score_warning_tags),
        "llm_fallback": False,
        "source": "GEMINI_RERANK",
    }


def _build_final_recommendations(
    *,
    rerank_result: RerankResult,
    scored_candidates: list[ScoredCaregiverCandidate],
) -> list[FinalRecommendation]:
    scored_by_id = {candidate.caregiver_id: candidate for candidate in scored_candidates}
    final_recommendations: list[FinalRecommendation] = []
    for item in sorted(rerank_result.recommendations, key=lambda recommendation: recommendation.rank):
        original_candidate = scored_by_id[item.caregiver_id]
        final_recommendations.append(
            FinalRecommendation(
                caregiver_id=item.caregiver_id,
                recommendation_rank=item.rank,
                match_score=item.final_score,
                recommendation_reason_json=_build_korean_reason_json(
                    reranked=item,
                    original_candidate=original_candidate,
                ),
                caregiver_snapshot_json=original_candidate.candidate,
            )
        )
    return final_recommendations


def _build_rerank_prompt(
    *,
    request_context: MatchingRequestContext,
    scored_candidates: list[ScoredCaregiverCandidate],
) -> str:
    compact_candidates: list[dict[str, Any]] = []
    for candidate in scored_candidates:
        raw_candidate = candidate.candidate
        person = raw_candidate.get("person") or {}
        compact_candidates.append(
            {
                "caregiver_id": candidate.caregiver_id,
                "caregiver_name": candidate.caregiver_name,
                "rule_total_score": candidate.total_score,
                "score_breakdown": candidate.score_breakdown.model_dump(mode="json"),
                "score_reason_tags": candidate.score_reason_tags,
                "score_warning_tags": candidate.score_warning_tags,
                "gender": person.get("gender"),
                "average_rating": raw_candidate.get("average_rating"),
                "rating_count": raw_candidate.get("rating_count"),
                "specialties": raw_candidate.get("specialties"),
                "tags": raw_candidate.get("tags", []),
                "history_metrics": candidate.history_metrics.model_dump(mode="json"),
            }
        )
    payload = {
        "request_context": request_context.model_dump(mode="json"),
        "scored_candidates": compact_candidates,
    }
    return "\n".join(
        [
            "You are the DUSON caregiver matching reranker.",
            "Select up to 3 caregivers from scored_candidates only.",
            "Do not invent caregiver_id values. Keep ranks continuous from 1.",
            "Use only request_context, score_breakdown, tags, specialties, and history_metrics as evidence.",
            "Every recommendation reason string must be natural Korean for Korean operators.",
            "Do not write English sentences or mix English words into summary, matched_points, risk_points, or score_adjustment_reason.",
            "Translate technical evidence such as mobility, rating, wage, schedule, and tag into plain Korean.",
            "Do not make medical judgments.",
            "Return JSON matching the provided schema.",
            "",
            "INPUT_JSON:",
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        ]
    )


class MatchingRecommendationAgent:
    def __init__(self, repository: MatchingRepository) -> None:
        self.repository = repository
        self.session = repository.session
        self.settings = get_settings()
        self._client: genai.Client | None = None

    async def run(
        self,
        matching_request_id: int,
    ) -> tuple[MatchingRequestRead, CallLogRead | None, list[MatchingRecommendationRead], MatchingCompletionRead | None]:
        request_context = await self._load_request_context(matching_request_id)
        request_start = request_context.proposed_start_datetime
        request_end = request_context.proposed_end_datetime or request_start + timedelta(days=1)

        candidates = await self._load_caregiver_candidates(
            matching_request_id=matching_request_id,
            request_start=request_start,
            request_end=request_end,
        )
        hard_filter_result = hard_filter_caregivers(request_context=request_context, candidates=candidates)
        if not hard_filter_result.eligible_candidates:
            raise NoEligibleCandidatesError("No eligible caregiver candidates passed the hard filter.")

        metrics_by_caregiver_id = await self._load_history_metrics(
            caregiver_ids=[candidate.caregiver_id for candidate in hard_filter_result.eligible_candidates],
            hospital_id=request_context.hospital_id,
        )
        scored_candidates = score_candidates_for_request(
            request_context=request_context,
            candidates=hard_filter_result.eligible_candidates,
            metrics_by_caregiver_id=metrics_by_caregiver_id,
            limit=20,
        )
        if not scored_candidates:
            raise NoEligibleCandidatesError("No caregiver candidates could be scored.")

        rerank_result = await self._rerank_with_gemini(
            request_context=request_context,
            scored_candidates=scored_candidates,
        )
        validate_rerank_result(rerank_result=rerank_result, scored_candidates=scored_candidates)
        final_recommendations = _build_final_recommendations(
            rerank_result=rerank_result,
            scored_candidates=scored_candidates,
        )
        await self._save_final_recommendations(
            matching_request_id=matching_request_id,
            final_recommendations=final_recommendations,
        )

        detail = await self.repository.get_matching_request_detail(matching_request_id)
        if not detail:
            raise MatchingRequestNotFoundError(f"Matching request {matching_request_id} was not found after recommendation save.")
        return detail

    async def _load_request_context(self, matching_request_id: int) -> MatchingRequestContext:
        row = (
            await self.session.execute(
                select(MatchingRequest, PatientProfile, Person, Hospital, MatchingRequestRequirement)
                .outerjoin(PatientProfile, MatchingRequest.patient_id == PatientProfile.patient_id)
                .outerjoin(Person, PatientProfile.person_id == Person.person_id)
                .outerjoin(Hospital, MatchingRequest.hospital_id == Hospital.hospital_id)
                .outerjoin(
                    MatchingRequestRequirement,
                    MatchingRequest.matching_request_id == MatchingRequestRequirement.matching_request_id,
                )
                .where(MatchingRequest.matching_request_id == matching_request_id)
            )
        ).one_or_none()
        if row is None:
            raise MatchingRequestNotFoundError(f"Matching request {matching_request_id} was not found.")

        request, patient, person, hospital, requirement = row
        if request.request_status in {"COMPLETED", "CANCELED"}:
            raise MatchingRequestNotRunnableError(f"Matching request status {request.request_status} cannot run recommendations.")

        return MatchingRequestContext(
            matching_request_id=request.matching_request_id,
            request_status=request.request_status,
            care_location_type=request.care_location_type,
            proposed_start_datetime=request.proposed_start_datetime,
            proposed_end_datetime=request.proposed_end_datetime,
            proposed_daily_wage=request.proposed_daily_wage,
            care_request_reason=request.care_request_reason,
            hospital_id=hospital.hospital_id if hospital else None,
            hospital_name=hospital.hospital_name if hospital else None,
            hospital_room=request.hospital_room,
            request_memo=request.request_memo,
            patient_id=patient.patient_id if patient else None,
            patient_name=person.name if person else request.patient_name_snapshot,
            patient_gender=person.gender if person else request.patient_gender_snapshot,
            patient_birth_date=(
                str(person.birth_date)
                if person and person.birth_date
                else str(request.patient_birth_date_snapshot)
                if request.patient_birth_date_snapshot
                else None
            ),
            requester_name=request.requester_name_snapshot or (patient.guardian_name if patient else None),
            requester_relationship=request.requester_relationship_snapshot or (patient.guardian_relationship if patient else None),
            requester_type=request.requester_type,
            requirement=self._requirement_context(requirement),
        )

    def _requirement_context(self, requirement: MatchingRequestRequirement | None) -> MatchingRequirementContext | None:
        if requirement is None:
            return None
        return MatchingRequirementContext(
            disease_note=requirement.disease_note,
            allergy_note=requirement.allergy_note,
            mobility_level=requirement.mobility_level,
            dementia_level=requirement.dementia_level,
            toileting_level=requirement.toileting_level,
            meal_assistance_level=requirement.meal_assistance_level,
            medication_required=bool(requirement.medication_required),
            rehab_required=bool(requirement.rehab_required),
            suction_required=bool(requirement.suction_required),
            night_care_required=bool(requirement.night_care_required),
            infection_precaution_required=bool(requirement.infection_precaution_required),
            preferred_caregiver_gender=requirement.preferred_caregiver_gender,
            care_intensity_level=requirement.care_intensity_level,
            preferred_conditions_json=requirement.preferred_conditions_json,
            care_instruction_json=requirement.care_instruction_json,
            special_note=requirement.special_note,
        )

    async def _load_caregiver_candidates(
        self,
        *,
        matching_request_id: int,
        request_start: datetime,
        request_end: datetime,
    ) -> list[CaregiverCandidate]:
        rows = (
            await self.session.execute(
                select(CaregiverProfile, Person)
                .join(Person, CaregiverProfile.person_id == Person.person_id)
                .order_by(CaregiverProfile.caregiver_id.asc())
            )
        ).all()
        caregiver_ids = [caregiver.caregiver_id for caregiver, _ in rows]
        person_id_to_caregiver_id = {caregiver.person_id: caregiver.caregiver_id for caregiver, _ in rows}
        tags_by_caregiver_id = await self._load_tags(caregiver_ids)
        contract_conflicts = await self._load_contract_conflicts(
            caregiver_ids=caregiver_ids,
            matching_request_id=matching_request_id,
            request_start=request_start,
            request_end=request_end,
        )
        care_service_conflicts = await self._load_care_service_conflicts(
            caregiver_ids=caregiver_ids,
            matching_request_id=matching_request_id,
            request_start=request_start,
            request_end=request_end,
        )
        temporary_assignment_conflicts = await self._load_temporary_assignment_conflicts(
            caregiver_ids=caregiver_ids,
            matching_request_id=matching_request_id,
            request_start=request_start,
            request_end=request_end,
        )
        schedule_conflicts = await self._load_schedule_conflicts(
            person_id_to_caregiver_id=person_id_to_caregiver_id,
            matching_request_id=matching_request_id,
            request_start=request_start,
            request_end=request_end,
        )

        return [
            CaregiverCandidate(
                caregiver_id=caregiver.caregiver_id,
                person=PersonBrief(
                    person_id=person.person_id,
                    name=person.name,
                    gender=person.gender,
                    phone=person.phone,
                    birth_date=str(person.birth_date) if person.birth_date else None,
                    profile_image_url=person.profile_image_url,
                ),
                person_is_active=bool(person.is_active),
                member_number=caregiver.member_number,
                caregiver_status=caregiver.caregiver_status,
                registered_at=str(caregiver.registered_at) if caregiver.registered_at else None,
                average_rating=caregiver.average_rating or Decimal("0"),
                rating_count=caregiver.rating_count or 0,
                specialties=caregiver.specialties,
                tags=tags_by_caregiver_id.get(caregiver.caregiver_id, []),
                has_contract_conflict=caregiver.caregiver_id in contract_conflicts,
                has_care_service_conflict=caregiver.caregiver_id in care_service_conflicts,
                has_temporary_assignment_conflict=caregiver.caregiver_id in temporary_assignment_conflicts,
                has_schedule_conflict=caregiver.caregiver_id in schedule_conflicts,
            )
            for caregiver, person in rows
        ]

    async def _load_tags(self, caregiver_ids: list[int]) -> dict[int, list[str]]:
        if not caregiver_ids:
            return {}
        rows = (
            await self.session.execute(
                select(CaregiverTag.caregiver_id, CaregiverTag.tag_name)
                .where(CaregiverTag.caregiver_id.in_(caregiver_ids))
                .order_by(CaregiverTag.caregiver_id.asc(), CaregiverTag.tag_name.asc())
            )
        ).all()
        tags: dict[int, list[str]] = {}
        for caregiver_id, tag_name in rows:
            if tag_name:
                tags.setdefault(caregiver_id, []).append(tag_name)
        return tags

    async def _load_contract_conflicts(
        self,
        *,
        caregiver_ids: list[int],
        matching_request_id: int,
        request_start: datetime,
        request_end: datetime,
    ) -> set[int]:
        if not caregiver_ids:
            return set()
        rows = (
            await self.session.execute(
                select(Contract.caregiver_id)
                .where(
                    Contract.caregiver_id.in_(caregiver_ids),
                    Contract.matching_request_id != matching_request_id,
                    Contract.contract_status.in_(["PENDING_SIGNATURE", "SIGNED", "ACTIVE"]),
                    Contract.start_datetime < request_end,
                    or_(Contract.end_datetime.is_(None), Contract.end_datetime > request_start),
                )
                .distinct()
            )
        ).all()
        return {caregiver_id for (caregiver_id,) in rows}

    async def _load_care_service_conflicts(
        self,
        *,
        caregiver_ids: list[int],
        matching_request_id: int,
        request_start: datetime,
        request_end: datetime,
    ) -> set[int]:
        if not caregiver_ids:
            return set()
        rows = (
            await self.session.execute(
                select(Contract.caregiver_id)
                .join(CareServiceLink, CareServiceLink.contract_id == Contract.contract_id)
                .join(CareService, CareServiceLink.care_service_id == CareService.care_service_id)
                .where(
                    Contract.caregiver_id.in_(caregiver_ids),
                    Contract.matching_request_id != matching_request_id,
                    CareService.service_status.in_(["PLANNED", "IN_PROGRESS"]),
                    CareService.planned_start_datetime < request_end,
                    or_(CareService.planned_end_datetime.is_(None), CareService.planned_end_datetime > request_start),
                )
                .distinct()
            )
        ).all()
        return {caregiver_id for (caregiver_id,) in rows}

    async def _load_temporary_assignment_conflicts(
        self,
        *,
        caregiver_ids: list[int],
        matching_request_id: int,
        request_start: datetime,
        request_end: datetime,
    ) -> set[int]:
        if not caregiver_ids:
            return set()
        rows = (
            await self.session.execute(
                select(TemporaryAssignment.caregiver_id)
                .where(
                    TemporaryAssignment.caregiver_id.in_(caregiver_ids),
                    TemporaryAssignment.matching_request_id != matching_request_id,
                    TemporaryAssignment.temporary_assignment_status.in_(
                        ["PROPOSED", "HOLDING", "CAREGIVER_ACCEPTED", "PATIENT_ACCEPTED", "CONFIRMED"]
                    ),
                    TemporaryAssignment.proposed_start_datetime < request_end,
                    or_(TemporaryAssignment.proposed_end_datetime.is_(None), TemporaryAssignment.proposed_end_datetime > request_start),
                )
                .distinct()
            )
        ).all()
        return {caregiver_id for (caregiver_id,) in rows}

    async def _load_schedule_conflicts(
        self,
        *,
        person_id_to_caregiver_id: dict[int, int],
        matching_request_id: int,
        request_start: datetime,
        request_end: datetime,
    ) -> set[int]:
        if not person_id_to_caregiver_id:
            return set()
        rows = (
            await self.session.execute(
                select(Schedule.related_person_id)
                .where(
                    Schedule.related_person_id.in_(list(person_id_to_caregiver_id.keys())),
                    or_(Schedule.matching_request_id.is_(None), Schedule.matching_request_id != matching_request_id),
                    Schedule.schedule_status.not_in(["CANCELED", "CANCELLED", "COMPLETED"]),
                    Schedule.start_datetime < request_end,
                    or_(Schedule.end_datetime.is_(None), Schedule.end_datetime > request_start),
                )
                .distinct()
            )
        ).all()
        return {
            person_id_to_caregiver_id[person_id]
            for (person_id,) in rows
            if person_id in person_id_to_caregiver_id
        }

    async def _load_history_metrics(
        self,
        *,
        caregiver_ids: list[int],
        hospital_id: int | None,
    ) -> dict[int, CandidateHistoryMetrics]:
        metrics_by_id = {caregiver_id: CandidateHistoryMetrics(caregiver_id=caregiver_id) for caregiver_id in caregiver_ids}
        if not caregiver_ids:
            return metrics_by_id

        contract_rows = (
            await self.session.execute(
                select(
                    Contract.caregiver_id,
                    func.count(Contract.contract_id),
                    func.sum(case((Contract.hospital_id == hospital_id, 1), else_=0)) if hospital_id is not None else literal(0),
                    func.avg(Contract.daily_wage),
                )
                .where(
                    Contract.caregiver_id.in_(caregiver_ids),
                    Contract.contract_status.in_(["SIGNED", "ACTIVE", "ENDED"]),
                )
                .group_by(Contract.caregiver_id)
            )
        ).all()
        for caregiver_id, total_count, same_hospital_count, average_daily_wage in contract_rows:
            metrics = metrics_by_id[caregiver_id]
            metrics.total_contract_count = int(total_count or 0)
            metrics.same_hospital_contract_count = int(same_hospital_count or 0)
            metrics.average_daily_wage = average_daily_wage

        review_rows = (
            await self.session.execute(
                select(
                    Contract.caregiver_id,
                    func.count(Review.review_id),
                    func.avg(Review.ai_score),
                )
                .join(CareServiceLink, CareServiceLink.contract_id == Contract.contract_id)
                .join(CareService, CareServiceLink.care_service_id == CareService.care_service_id)
                .join(Review, Review.care_service_id == CareService.care_service_id)
                .where(
                    Contract.caregiver_id.in_(caregiver_ids),
                    Review.review_status.in_(["REVIEW_RECEIVED", "COMPLETED"]),
                )
                .group_by(Contract.caregiver_id)
            )
        ).all()
        for caregiver_id, review_count, average_ai_score in review_rows:
            metrics = metrics_by_id[caregiver_id]
            metrics.review_count = int(review_count or 0)
            metrics.average_ai_score = average_ai_score
        return metrics_by_id

    async def _rerank_with_gemini(
        self,
        *,
        request_context: MatchingRequestContext,
        scored_candidates: list[ScoredCaregiverCandidate],
    ) -> RerankResult:
        if not self.settings.gemini_api_key:
            raise MatchingRecommendationLLMError("GEMINI_API_KEY or GOOGLE_API_KEY is not configured.")
        prompt = _build_rerank_prompt(
            request_context=request_context,
            scored_candidates=scored_candidates[:20],
        )
        return await asyncio.to_thread(self._rerank_with_gemini_sync, prompt)

    def _rerank_with_gemini_sync(self, prompt: str) -> RerankResult:
        response = None
        try:
            response = self._client_or_create().models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RerankResult,
                    temperature=0,
                    top_p=0.8,
                    max_output_tokens=min(self.settings.gemini_max_output_tokens, 2048),
                ),
            )
            if getattr(response, "parsed", None) is not None:
                return RerankResult.model_validate(response.parsed)
            return RerankResult.model_validate_json(response.text or "")
        except ValidationError as exc:
            raise MatchingRecommendationLLMError(f"Gemini recommendation response schema validation failed: {exc}") from exc
        except Exception as exc:
            raw_text = getattr(response, "text", None)
            suffix = f" raw={raw_text[:300]}" if raw_text else ""
            raise MatchingRecommendationLLMError(f"Gemini recommendation call failed: {exc}{suffix}") from exc

    def _client_or_create(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    async def _save_final_recommendations(
        self,
        *,
        matching_request_id: int,
        final_recommendations: list[FinalRecommendation],
    ) -> None:
        if not final_recommendations:
            raise MatchingRecommendationLLMError("No final recommendations to save.")
        now = datetime.now(timezone.utc)
        request = await self.session.get(MatchingRequest, matching_request_id)
        if not request:
            raise MatchingRequestNotFoundError(f"Matching request {matching_request_id} was not found.")
        if request.request_status in {"COMPLETED", "CANCELED"}:
            raise MatchingRequestNotRunnableError(f"Matching request status {request.request_status} cannot save recommendations.")

        try:
            await self.session.execute(
                delete(MatchingRecommendation).where(MatchingRecommendation.matching_request_id == matching_request_id)
            )
            for item in final_recommendations:
                self.session.add(
                    MatchingRecommendation(
                        matching_request_id=matching_request_id,
                        caregiver_id=item.caregiver_id,
                        recommendation_rank=item.recommendation_rank,
                        match_score=Decimal(str(round(item.match_score, 2))),
                        recommendation_reason_json=item.recommendation_reason_json,
                        caregiver_snapshot_json=item.caregiver_snapshot_json,
                        recommendation_status="RECOMMENDED",
                        created_at=now,
                        updated_at=now,
                    )
                )
            request.request_status = "RECOMMENDED"
            request.updated_at = now
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
