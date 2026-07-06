from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class LearnerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    default_system_language: str = "en"
    learning_language: str = "ko"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("A valid email address is required.")
        return normalized


class LearnerResponse(BaseModel):
    learner_id: UUID
    email: str
    name: str
    created: bool


class DailyPracticeQuestion(BaseModel):
    quiz_item_id: UUID
    item_order: int
    quiz_item_code: str
    item_type_code: str
    variant_code: str
    skill_code: str
    assessment_skill_id: UUID
    prompt: str
    item_content: dict[str, Any]
    answer_data: dict[str, Any]


class DailyPracticeActivityResponse(BaseModel):
    assessment_activity_id: UUID
    activity_code: str
    activity_name: str
    unit_id: UUID
    unit_code: str
    total_questions: int
    questions: list[DailyPracticeQuestion]


class AttemptCreateRequest(BaseModel):
    learner_id: UUID
    activity_code: str


class AttemptResponse(BaseModel):
    learner_assessment_attempt_id: UUID
    learner_id: UUID
    assessment_activity_id: UUID
    status: str


class SubmittedAnswer(BaseModel):
    quiz_item_id: UUID
    selected_option_key: str | None = None
    selected_order: list[str] | None = None
    response_status: str | None = Field(
        default=None,
        description="Optional override: correct, incorrect, unsure, or skipped.",
    )


class AttemptSubmitRequest(BaseModel):
    answers: list[SubmittedAnswer]


class SkillResultResponse(BaseModel):
    learner_assessment_skill_result_id: UUID
    assessment_skill_id: UUID
    skill_code: str
    skill_score: float
    result_detail: dict[str, Any]
    mastery_score: float


class AttemptSubmitResponse(BaseModel):
    learner_assessment_attempt_id: UUID
    learner_id: UUID
    assessment_activity_id: UUID
    status: str
    total_questions: int
    correct_count: int
    incorrect_count: int
    unsure_count: int
    skipped_count: int
    skill_results: list[SkillResultResponse]
