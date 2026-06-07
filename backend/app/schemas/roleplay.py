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
    "offTopic",
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
    current_step_order: int
    current_step_guidance_text: str | None = None
    total_steps: int
    should_show_feedback: bool


class RoleplayTurnMessage(BaseModel):
    message_id: str | None = None
    sender_type: Literal["system", "roleplay_character", "learner"]
    message_type: Literal[
        "scene_text",
        "roleplay_character_action_text",
        "roleplay_character_dialogue_text",
        "learner_input_text",
        "hint",
        "correction_feedback",
    ]
    text_content: str
    text_language: Literal["en", "ko"]
    translation_json: dict | None = None
    step_id: str | None = None
    hint_level: str | None = None


class RoleplaySessionStatus(BaseModel):
    end_status: str
    is_ended: bool
    current_step_id: str | None = None
    created_turn_id: str | None = None


class RoleplayTurnResponse(BaseModel):
    transcript: str
    assistant_message: AssistantMessage
    evaluation: Evaluation
    feedback: CorrectionFeedback | None = None
    ui_state: RoleplayUiState
    turn_messages: list[RoleplayTurnMessage] = Field(default_factory=list)
    session_status: RoleplaySessionStatus | None = None


class RoleplayScenarioSummary(BaseModel):
    scenario_id: str
    title: str
    description: str
    difficulty: str


class RoleplayVersionSummary(BaseModel):
    scenario_version_id: str
    learning_language: str
    default_system_language: str
    default_total_chances: int


class RoleplayLocationSummary(BaseModel):
    scenario_location_id: str
    roleplay_location_id: str
    name: str
    description: str
    background_image_url: str | None = None


class RoleplayCharacterSummary(BaseModel):
    scenario_roleplay_character_id: str
    roleplay_character_id: str
    role_name: str
    name: str
    description: str
    image_url: str | None = None


class StepSampleAnswerSummary(BaseModel):
    step_sample_answer_id: str
    text: str
    language_code: str
    display_order: int


class CurrentRoleplayStep(BaseModel):
    step_id: str
    step_order: int
    step_title: str
    step_goal: str
    guidance_text: str | None = None
    scene_text: str | None = None
    character_action_text: str | None = None
    character_dialogue_text: str | None = None
    character_dialogue_language: str
    character_dialogue_translation_json: dict | None = None
    sample_answers: list[StepSampleAnswerSummary] = Field(default_factory=list)


class RoleplayIngameUiState(BaseModel):
    total_chances: int
    remaining_chances: int
    score_count: int = 0
    current_step_order: int
    total_steps: int


class RoleplayIngameResponse(BaseModel):
    scenario: RoleplayScenarioSummary
    version: RoleplayVersionSummary
    location: RoleplayLocationSummary
    character: RoleplayCharacterSummary
    current_step: CurrentRoleplayStep
    ui_state: RoleplayIngameUiState


class RoleplaySessionCreateRequest(BaseModel):
    learner_id: str
    scenario_version_id: str | None = None


class RoleplaySessionCreateResponse(BaseModel):
    roleplay_session_id: str
    learner_id: str
    scenario_version_id: str
    current_step_id: str
    total_chances: int
    remaining_chances: int
    end_status: str
    current_step_fail_count: int
