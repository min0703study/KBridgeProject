from __future__ import annotations

from typing import Any, Literal

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


MessageType = Literal[
    "scene_text",
    "roleplay_character_action_text",
    "roleplay_character_dialogue_text",
    "hint",
    "correction_feedback",
]


class ResponseMessageDraft(BaseModel):
    message_type: MessageType
    text_content: str
    text_language: Literal["en", "ko"]
    translation_json: dict[str, Any] | None = None
    step_id: str | None = None
    scenario_roleplay_character_id: str | None = None
    hint_level: Literal["light", "medium", "strong"] | None = None


class ResponsePack(BaseModel):
    message_drafts: list[ResponseMessageDraft] = Field(default_factory=list)
    correction_items: list[CorrectionItem] = Field(default_factory=list)

    @property
    def scene_text(self) -> str | None:
        return self._first_text("scene_text")

    @property
    def character_action_text(self) -> str | None:
        return self._first_text("roleplay_character_action_text")

    @property
    def character_dialogue_text(self) -> str | None:
        return self._first_text("roleplay_character_dialogue_text")

    @property
    def character_dialogue_translation_text(self) -> str | None:
        draft = self._first_draft("roleplay_character_dialogue_text")
        if not draft or not draft.translation_json:
            return None
        value = draft.translation_json.get("en")
        return value if isinstance(value, str) else None

    @property
    def hint_text(self) -> str | None:
        return self._first_text("hint")

    def _first_text(self, message_type: MessageType) -> str | None:
        draft = self._first_draft(message_type)
        return draft.text_content if draft else None

    def _first_draft(self, message_type: MessageType) -> ResponseMessageDraft | None:
        return next(
            (
                draft
                for draft in self.message_drafts
                if draft.message_type == message_type
            ),
            None,
        )


class FinalFeedbackResult(BaseModel):
    final_feedback_text: str
    strengths: list[str] = Field(default_factory=list)
    improvement_points: list[str] = Field(default_factory=list)
    repeated_issue_tags: list[IssueTag] = Field(default_factory=list)
