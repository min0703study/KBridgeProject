from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


UserRoleEnum = ENUM("learner", "teacher", "admin", name="user_role_enum", create_type=False)
UserStatusEnum = ENUM("active", "inactive", "deleted", name="user_status_enum", create_type=False)
LanguageCodeEnum = ENUM("en", "ko", name="language_code_enum", create_type=False)
ScenarioStatusEnum = ENUM("draft", "published", "archived", name="scenario_status_enum", create_type=False)
DifficultyEnum = ENUM("beginner", "intermediate", "advanced", name="difficulty_enum", create_type=False)
SessionEndStatusEnum = ENUM(
    "in_progress",
    "completed",
    "failed",
    "abandoned",
    name="session_end_status_enum",
    create_type=False,
)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(UserRoleEnum)
    default_system_language: Mapped[str] = mapped_column(LanguageCodeEnum)
    status: Mapped[str] = mapped_column(UserStatusEnum)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FileAsset(Base):
    __tablename__ = "file_assets"

    file_asset_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    asset_type: Mapped[str] = mapped_column(String)
    storage_key: Mapped[str] = mapped_column(Text)
    public_url: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB)
    status: Mapped[str] = mapped_column(String)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RoleplayLocation(Base):
    __tablename__ = "roleplay_locations"

    roleplay_location_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    background_image_file_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("file_assets.file_asset_id")
    )
    location_prompt: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    background_image: Mapped[FileAsset | None] = relationship()


class RoleplayCharacter(Base):
    __tablename__ = "roleplay_characters"

    roleplay_character_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    image_base_file_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("file_assets.file_asset_id")
    )
    persona_prompt: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    image_base: Mapped[FileAsset | None] = relationship()


class Scenario(Base):
    __tablename__ = "scenarios"

    scenario_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(DifficultyEnum)
    thumbnail_file_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("file_assets.file_asset_id")
    )
    status: Mapped[str] = mapped_column(ScenarioStatusEnum)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    thumbnail: Mapped[FileAsset | None] = relationship()


class ScenarioVersion(Base):
    __tablename__ = "scenario_versions"

    scenario_version_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    scenario_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("scenarios.scenario_id"))
    version_number: Mapped[int] = mapped_column(Integer)
    learning_language: Mapped[str] = mapped_column(LanguageCodeEnum)
    default_system_language: Mapped[str] = mapped_column(LanguageCodeEnum)
    default_total_chances: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(ScenarioStatusEnum)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    scenario: Mapped[Scenario] = relationship()


class ScenarioLocation(Base):
    __tablename__ = "scenario_locations"

    scenario_location_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    scenario_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("scenario_versions.scenario_version_id")
    )
    roleplay_location_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("roleplay_locations.roleplay_location_id")
    )
    display_order: Mapped[int] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    roleplay_location: Mapped[RoleplayLocation] = relationship()


class ScenarioRoleplayCharacter(Base):
    __tablename__ = "scenario_roleplay_characters"

    scenario_roleplay_character_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    scenario_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("scenario_versions.scenario_version_id")
    )
    roleplay_character_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("roleplay_characters.roleplay_character_id")
    )
    scenario_role_name: Mapped[str] = mapped_column(String(100))
    display_order: Mapped[int] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    roleplay_character: Mapped[RoleplayCharacter] = relationship()


class Step(Base):
    __tablename__ = "steps"

    step_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    scenario_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("scenario_versions.scenario_version_id")
    )
    step_order: Mapped[int] = mapped_column(Integer)
    step_title: Mapped[str] = mapped_column(String(255))
    step_goal: Mapped[str] = mapped_column(Text)
    initial_scene_text: Mapped[str | None] = mapped_column(Text)
    initial_roleplay_character_action_text: Mapped[str | None] = mapped_column(Text)
    initial_roleplay_character_dialogue_text: Mapped[str | None] = mapped_column(Text)
    initial_roleplay_character_dialogue_language: Mapped[str] = mapped_column(LanguageCodeEnum)
    initial_roleplay_character_dialogue_translation_json: Mapped[dict | None] = mapped_column(JSONB)
    roleplay_guidance_text: Mapped[str | None] = mapped_column(Text)
    primary_scenario_roleplay_character_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("scenario_roleplay_characters.scenario_roleplay_character_id")
    )
    primary_scenario_location_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("scenario_locations.scenario_location_id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StepSampleAnswer(Base):
    __tablename__ = "step_sample_answers"

    step_sample_answer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    step_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("steps.step_id"))
    sample_answer_text: Mapped[str] = mapped_column(Text)
    language_code: Mapped[str] = mapped_column(LanguageCodeEnum)
    display_order: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RoleplaySession(Base):
    __tablename__ = "roleplay_sessions"

    roleplay_session_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    learner_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.user_id"))
    scenario_version_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("scenario_versions.scenario_version_id")
    )
    current_step_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("steps.step_id"))
    total_chances: Mapped[int] = mapped_column(Integer)
    remaining_chances: Mapped[int] = mapped_column(Integer)
    end_status: Mapped[str] = mapped_column(SessionEndStatusEnum)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_step_fail_count: Mapped[int] = mapped_column(Integer)

    learner: Mapped[User] = relationship()
    scenario_version: Mapped[ScenarioVersion] = relationship()
    current_step: Mapped[Step | None] = relationship()
