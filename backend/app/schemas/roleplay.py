from typing import Literal

from pydantic import BaseModel, Field


EvaluationResult = Literal["pass", "soft_pass", "fail"]
IssueTag = Literal[
    "grammar",
    "vocabulary",
    "politeness",
    "naturalness",
    "culturalContext",
    "taskExpression",
    "clarity",
]


class AssistantMessage(BaseModel):
    ko: str
    en: str
    audio_base64: str
    audio_mime_type: str = "audio/mpeg"


class Evaluation(BaseModel):
    result: EvaluationResult
    issue_tags: list[IssueTag] = Field(default_factory=list)
    correction_needed: bool = False


class CorrectionFeedback(BaseModel):
    previous_text: str
    better_way: str
    politeness_note: str
    grammar_note: str


class RoleplayUiState(BaseModel):
    remaining_chances: int
    score_count: int
    current_step_label: str
    should_show_feedback: bool


class RoleplayTurnResponse(BaseModel):
    transcript: str
    assistant_message: AssistantMessage
    evaluation: Evaluation
    feedback: CorrectionFeedback | None = None
    ui_state: RoleplayUiState
