-- KBridge current application schema
-- Source of truth: backend/app/db/models.py
-- PostgreSQL

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role_enum') THEN
        CREATE TYPE user_role_enum AS ENUM ('learner', 'teacher', 'admin');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_status_enum') THEN
        CREATE TYPE user_status_enum AS ENUM ('active', 'inactive', 'deleted');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'language_code_enum') THEN
        CREATE TYPE language_code_enum AS ENUM ('en', 'ko');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'scenario_status_enum') THEN
        CREATE TYPE scenario_status_enum AS ENUM ('draft', 'published', 'archived');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'difficulty_enum') THEN
        CREATE TYPE difficulty_enum AS ENUM ('beginner', 'intermediate', 'advanced');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'session_end_status_enum') THEN
        CREATE TYPE session_end_status_enum AS ENUM ('in_progress', 'completed', 'failed', 'abandoned');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'input_method_enum') THEN
        CREATE TYPE input_method_enum AS ENUM ('voice', 'text');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sender_type_enum') THEN
        CREATE TYPE sender_type_enum AS ENUM ('system', 'roleplay_character', 'learner');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_generated_by_enum') THEN
        CREATE TYPE message_generated_by_enum AS ENUM ('system', 'ai_agent', 'admin');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_type_enum') THEN
        CREATE TYPE message_type_enum AS ENUM (
            'scene_text',
            'roleplay_character_action_text',
            'roleplay_character_dialogue_text',
            'learner_input_text',
            'hint',
            'correction_feedback'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'evaluation_result_enum') THEN
        CREATE TYPE evaluation_result_enum AS ENUM ('pass', 'soft_pass', 'fail');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS users (
    user_id uuid PRIMARY KEY,
    email varchar(255) NOT NULL,
    name varchar(100) NOT NULL,
    role user_role_enum NOT NULL,
    default_system_language language_code_enum NOT NULL,
    status user_status_enum NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS file_assets (
    file_asset_id uuid PRIMARY KEY,
    original_filename varchar(255) NOT NULL,
    mime_type varchar(100) NOT NULL,
    asset_type varchar NOT NULL,
    storage_key text NOT NULL,
    public_url text,
    file_size_bytes bigint,
    metadata jsonb,
    status varchar NOT NULL,
    created_by_user_id uuid,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS roleplay_locations (
    roleplay_location_id uuid PRIMARY KEY,
    name varchar(100) NOT NULL,
    description text NOT NULL,
    background_image_file_id uuid REFERENCES file_assets(file_asset_id),
    location_prompt text,
    status varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS roleplay_characters (
    roleplay_character_id uuid PRIMARY KEY,
    name varchar(100) NOT NULL,
    description text NOT NULL,
    image_base_file_id uuid REFERENCES file_assets(file_asset_id),
    persona_prompt text,
    status varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id uuid PRIMARY KEY,
    title varchar(255) NOT NULL,
    description text NOT NULL,
    difficulty difficulty_enum NOT NULL,
    thumbnail_file_id uuid REFERENCES file_assets(file_asset_id),
    status scenario_status_enum NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_versions (
    scenario_version_id uuid PRIMARY KEY,
    scenario_id uuid NOT NULL REFERENCES scenarios(scenario_id),
    version_number integer NOT NULL,
    learning_language language_code_enum NOT NULL,
    default_system_language language_code_enum NOT NULL,
    default_total_chances integer NOT NULL,
    status scenario_status_enum NOT NULL,
    published_at timestamptz,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_locations (
    scenario_location_id uuid PRIMARY KEY,
    scenario_version_id uuid NOT NULL REFERENCES scenario_versions(scenario_version_id),
    roleplay_location_id uuid NOT NULL REFERENCES roleplay_locations(roleplay_location_id),
    display_order integer NOT NULL,
    is_primary boolean NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_roleplay_characters (
    scenario_roleplay_character_id uuid PRIMARY KEY,
    scenario_version_id uuid NOT NULL REFERENCES scenario_versions(scenario_version_id),
    roleplay_character_id uuid NOT NULL REFERENCES roleplay_characters(roleplay_character_id),
    scenario_role_name varchar(100) NOT NULL,
    display_order integer NOT NULL,
    is_primary boolean NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS steps (
    step_id uuid PRIMARY KEY,
    scenario_version_id uuid NOT NULL REFERENCES scenario_versions(scenario_version_id),
    step_order integer NOT NULL,
    step_title varchar(255) NOT NULL,
    step_goal text NOT NULL,
    initial_scene_text text,
    initial_roleplay_character_action_text text,
    initial_roleplay_character_dialogue_text text,
    initial_roleplay_character_dialogue_language language_code_enum NOT NULL,
    initial_roleplay_character_dialogue_translation_json jsonb,
    roleplay_guidance_text text,
    primary_scenario_roleplay_character_id uuid REFERENCES scenario_roleplay_characters(scenario_roleplay_character_id),
    primary_scenario_location_id uuid REFERENCES scenario_locations(scenario_location_id),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS step_sample_answers (
    step_sample_answer_id uuid PRIMARY KEY,
    step_id uuid NOT NULL REFERENCES steps(step_id),
    sample_answer_text text NOT NULL,
    language_code language_code_enum NOT NULL,
    display_order integer NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS roleplay_sessions (
    roleplay_session_id uuid PRIMARY KEY,
    learner_id uuid NOT NULL REFERENCES users(user_id),
    scenario_version_id uuid NOT NULL REFERENCES scenario_versions(scenario_version_id),
    current_step_id uuid REFERENCES steps(step_id),
    total_chances integer NOT NULL,
    remaining_chances integer NOT NULL,
    end_status session_end_status_enum NOT NULL,
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    current_step_fail_count integer NOT NULL
);

CREATE TABLE IF NOT EXISTS roleplay_turns (
    roleplay_turn_id uuid PRIMARY KEY,
    roleplay_session_id uuid NOT NULL REFERENCES roleplay_sessions(roleplay_session_id),
    step_id uuid NOT NULL REFERENCES steps(step_id),
    next_step_id uuid REFERENCES steps(step_id),
    turn_order integer NOT NULL,
    input_method input_method_enum NOT NULL,
    remaining_chances_before integer NOT NULL,
    remaining_chances_after integer NOT NULL,
    end_status_after session_end_status_enum,
    created_at timestamptz NOT NULL,
    fail_count_before integer NOT NULL,
    fail_count_after integer NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    message_id uuid PRIMARY KEY,
    roleplay_session_id uuid NOT NULL REFERENCES roleplay_sessions(roleplay_session_id),
    roleplay_turn_id uuid,
    step_id uuid REFERENCES steps(step_id),
    scenario_roleplay_character_id uuid REFERENCES scenario_roleplay_characters(scenario_roleplay_character_id),
    message_order integer NOT NULL,
    sender_type sender_type_enum NOT NULL,
    generated_by message_generated_by_enum,
    message_type message_type_enum NOT NULL,
    text_content text NOT NULL,
    text_language language_code_enum NOT NULL,
    translation_json jsonb,
    audio_file_id uuid,
    created_at timestamptz NOT NULL,
    hint_level varchar
);

CREATE TABLE IF NOT EXISTS roleplay_evaluations (
    roleplay_evaluation_id uuid PRIMARY KEY,
    roleplay_turn_id uuid NOT NULL REFERENCES roleplay_turns(roleplay_turn_id),
    roleplay_session_id uuid NOT NULL REFERENCES roleplay_sessions(roleplay_session_id),
    step_id uuid NOT NULL REFERENCES steps(step_id),
    evaluation_order integer NOT NULL,
    learner_input_text text NOT NULL,
    evaluation_result evaluation_result_enum NOT NULL,
    inferred_intent_text text,
    step_goal_matched boolean,
    evaluation_reason_text text,
    correction_json jsonb,
    cultural_issue_detected boolean,
    should_advance_step boolean NOT NULL,
    should_decrease_chance boolean NOT NULL,
    should_end_session boolean NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_scenario_versions_scenario_id
    ON scenario_versions(scenario_id);
CREATE INDEX IF NOT EXISTS ix_scenario_locations_version_order
    ON scenario_locations(scenario_version_id, display_order);
CREATE INDEX IF NOT EXISTS ix_scenario_roleplay_characters_version_order
    ON scenario_roleplay_characters(scenario_version_id, display_order);
CREATE INDEX IF NOT EXISTS ix_steps_version_order
    ON steps(scenario_version_id, step_order);
CREATE INDEX IF NOT EXISTS ix_step_sample_answers_step_order
    ON step_sample_answers(step_id, display_order);
CREATE INDEX IF NOT EXISTS ix_roleplay_sessions_learner
    ON roleplay_sessions(learner_id);
CREATE INDEX IF NOT EXISTS ix_roleplay_sessions_version
    ON roleplay_sessions(scenario_version_id);
CREATE INDEX IF NOT EXISTS ix_roleplay_turns_session_order
    ON roleplay_turns(roleplay_session_id, turn_order);
CREATE INDEX IF NOT EXISTS ix_messages_session_order
    ON messages(roleplay_session_id, message_order);
CREATE INDEX IF NOT EXISTS ix_roleplay_evaluations_session_order
    ON roleplay_evaluations(roleplay_session_id, evaluation_order);

COMMIT;
