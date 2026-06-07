from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


EvaluationResult = Literal["pass", "soft_pass", "fail"]
InputMethod = Literal["voice", "text"]
ProgressOutcome = Literal[
    "stay_current_step",
    "advance_to_next_step",
    "complete_session",
    "fail_session",
]
IssueTag = Literal[
    "grammar",
    "vocabulary",
    "politeness",
    "naturalness",
    "culturalContext",
    "taskExpression",
    "clarity",
    "offTopic",
]


class RetrievedKnowledge(BaseModel):
    document_id: str
    category: str
    subject: str
    chunk_index: int
    chunk_text: str
    similarity_score: float | None = None
    keyword_boost: float = 0.0
    final_score: float
    matched_keywords: list[str] = Field(default_factory=list)


class CorrectionItem(BaseModel):
    type: IssueTag
    original_text: str
    corrected_text: str
    reason_text: str


class JudgeResult(BaseModel):
    evaluation_result: EvaluationResult
    confidence: float
    inferred_intent_text: str
    step_goal_matched: bool
    communication_success: bool
    issue_tags: list[IssueTag] = Field(default_factory=list)
    correction_needed: bool = False
    cultural_issue_detected: bool = False
    evaluation_reason_text: str


class RuleDecision(BaseModel):
    evaluation_result: EvaluationResult
    progress_outcome: ProgressOutcome
    current_step_id: str
    next_step_id: str | None = None
    should_advance_step: bool
    should_decrease_chance: bool
    should_end_session: bool
    remaining_chances_before: int
    remaining_chances_after: int
    current_step_fail_count_before: int
    current_step_fail_count_after: int
    end_status_after: Literal["in_progress", "completed", "failed"]
    hint_level: Literal["none", "light", "medium", "strong"]
    transition_reason: str


class ResponsePack(BaseModel):
    scene_text: str | None = None
    character_action_text: str | None = None
    character_dialogue_text: str | None = None
    character_dialogue_translation_text: str | None = None
    hint_text: str | None = None
    correction_items: list[CorrectionItem] = Field(default_factory=list)


class FinalFeedbackResult(BaseModel):
    final_feedback_text: str
    strengths: list[str] = Field(default_factory=list)
    improvement_points: list[str] = Field(default_factory=list)
    repeated_issue_tags: list[IssueTag] = Field(default_factory=list)
