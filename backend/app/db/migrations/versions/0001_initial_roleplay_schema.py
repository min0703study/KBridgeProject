"""Initial roleplay schema — provisions the `roleplay` PostgreSQL schema, its 11 enum types,
and its 14 tables, matching backend/app/db/models.py exactly.

This repo previously had no Alembic tracking at all (no `Base.metadata.create_all()` call
anywhere, all 11 enum types declared `create_type=False`) — whatever database backs this app
was provisioned entirely out-of-band. This migration is the first one, and it is intentionally
NOT a destructive "reconcile with existing state" migration:

- It creates the `roleplay` schema and, within it, every enum/table `IF NOT EXISTS` /
  guarded against `duplicate_object` — additive and idempotent, safe to run against an empty
  database or re-run against one that already has this exact shape.
- It does **not** touch anything in the `public` schema. If this environment previously ran
  with these same tables/types living in `public` (unqualified, pre-schema-separation), this
  migration will NOT move that data — it only creates fresh objects under `roleplay`. Moving
  pre-existing `public.users` / `public.scenarios` / etc. data into `roleplay` (via
  `ALTER TABLE public.x SET SCHEMA roleplay`, table by table) is a manual, environment-specific
  step for whoever operates that database, since only they can confirm whether real data is
  there. Do not run that move blindly against a shared instance.
- The schema separation itself exists because this app's default `DATABASE_URL` points at a
  `kBridge` database that the K-Bridge admin hub repo (`k_bridge_admin`) also uses, whose own
  `scripts/db/schema.sql` defines unrelated `public.users` / `public.scenarios` tables with a
  different shape. Namespacing this app's tables under `roleplay` avoids that collision going
  forward.

Each statement is executed individually (not as one multi-statement string) because asyncpg
prepares every statement and Postgres prepared statements cannot contain multiple commands
(`asyncpg.exceptions.PostgresSyntaxError: cannot insert multiple commands into a prepared
statement`) — this bit even a single `DO $$ ... END $$;` block followed by another statement
in the same `op.execute()` call.

Revision ID: 0001
Revises: (none — first migration)
"""

from alembic import op


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_UP_STATEMENTS = [
    "CREATE SCHEMA IF NOT EXISTS roleplay",
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.user_role_enum AS ENUM ('learner', 'teacher', 'admin');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.user_status_enum AS ENUM ('active', 'inactive', 'deleted');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.language_code_enum AS ENUM ('en', 'ko');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.scenario_status_enum AS ENUM ('draft', 'published', 'archived');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.difficulty_enum AS ENUM ('beginner', 'intermediate', 'advanced');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.session_end_status_enum AS ENUM ('in_progress', 'completed', 'failed', 'abandoned');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.input_method_enum AS ENUM ('voice', 'text');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.sender_type_enum AS ENUM ('system', 'roleplay_character', 'learner');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.message_generated_by_enum AS ENUM ('system', 'ai_agent', 'admin');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.message_type_enum AS ENUM (
        'scene_text', 'roleplay_character_action_text', 'roleplay_character_dialogue_text',
        'learner_input_text', 'hint', 'correction_feedback'
      );
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    DO $$ BEGIN
      CREATE TYPE roleplay.evaluation_result_enum AS ENUM ('pass', 'soft_pass', 'fail');
    EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.users (
      user_id                 uuid PRIMARY KEY,
      email                   varchar(255) NOT NULL,
      name                    varchar(100) NOT NULL,
      role                    roleplay.user_role_enum NOT NULL,
      default_system_language roleplay.language_code_enum NOT NULL,
      status                  roleplay.user_status_enum NOT NULL,
      created_at              timestamptz NOT NULL,
      updated_at              timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.file_assets (
      file_asset_id      uuid PRIMARY KEY,
      original_filename  varchar(255) NOT NULL,
      mime_type          varchar(100) NOT NULL,
      asset_type         varchar NOT NULL,
      storage_key        text NOT NULL,
      public_url         text,
      file_size_bytes    bigint,
      metadata           jsonb,
      status             varchar NOT NULL,
      created_by_user_id uuid,
      created_at         timestamptz NOT NULL,
      updated_at         timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.roleplay_locations (
      roleplay_location_id     uuid PRIMARY KEY,
      name                     varchar(100) NOT NULL,
      description              text NOT NULL,
      background_image_file_id uuid REFERENCES roleplay.file_assets(file_asset_id),
      location_prompt          text,
      status                   varchar NOT NULL,
      created_at               timestamptz NOT NULL,
      updated_at               timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.roleplay_characters (
      roleplay_character_id uuid PRIMARY KEY,
      name                   varchar(100) NOT NULL,
      description            text NOT NULL,
      image_base_file_id     uuid REFERENCES roleplay.file_assets(file_asset_id),
      persona_prompt         text,
      status                 varchar NOT NULL,
      created_at             timestamptz NOT NULL,
      updated_at             timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.scenarios (
      scenario_id       uuid PRIMARY KEY,
      title             varchar(255) NOT NULL,
      description       text NOT NULL,
      difficulty        roleplay.difficulty_enum NOT NULL,
      thumbnail_file_id uuid REFERENCES roleplay.file_assets(file_asset_id),
      status            roleplay.scenario_status_enum NOT NULL,
      created_at        timestamptz NOT NULL,
      updated_at        timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.scenario_versions (
      scenario_version_id     uuid PRIMARY KEY,
      scenario_id              uuid NOT NULL REFERENCES roleplay.scenarios(scenario_id),
      version_number            integer NOT NULL,
      learning_language          roleplay.language_code_enum NOT NULL,
      default_system_language    roleplay.language_code_enum NOT NULL,
      default_total_chances      integer NOT NULL,
      status                     roleplay.scenario_status_enum NOT NULL,
      published_at               timestamptz,
      created_at                 timestamptz NOT NULL,
      updated_at                 timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.scenario_locations (
      scenario_location_id  uuid PRIMARY KEY,
      scenario_version_id    uuid NOT NULL REFERENCES roleplay.scenario_versions(scenario_version_id),
      roleplay_location_id    uuid NOT NULL REFERENCES roleplay.roleplay_locations(roleplay_location_id),
      display_order           integer NOT NULL,
      is_primary              boolean NOT NULL,
      created_at              timestamptz NOT NULL,
      updated_at              timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.scenario_roleplay_characters (
      scenario_roleplay_character_id uuid PRIMARY KEY,
      scenario_version_id             uuid NOT NULL REFERENCES roleplay.scenario_versions(scenario_version_id),
      roleplay_character_id           uuid NOT NULL REFERENCES roleplay.roleplay_characters(roleplay_character_id),
      scenario_role_name              varchar(100) NOT NULL,
      display_order                   integer NOT NULL,
      is_primary                      boolean NOT NULL,
      created_at                      timestamptz NOT NULL,
      updated_at                      timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.steps (
      step_id                                              uuid PRIMARY KEY,
      scenario_version_id                                   uuid NOT NULL REFERENCES roleplay.scenario_versions(scenario_version_id),
      step_order                                            integer NOT NULL,
      step_title                                            varchar(255) NOT NULL,
      step_goal                                             text NOT NULL,
      initial_scene_text                                    text,
      initial_roleplay_character_action_text                text,
      initial_roleplay_character_dialogue_text              text,
      initial_roleplay_character_dialogue_language          roleplay.language_code_enum NOT NULL,
      initial_roleplay_character_dialogue_translation_json  jsonb,
      roleplay_guidance_text                                text,
      primary_scenario_roleplay_character_id                uuid REFERENCES roleplay.scenario_roleplay_characters(scenario_roleplay_character_id),
      primary_scenario_location_id                          uuid REFERENCES roleplay.scenario_locations(scenario_location_id),
      created_at                                            timestamptz NOT NULL,
      updated_at                                            timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.step_sample_answers (
      step_sample_answer_id uuid PRIMARY KEY,
      step_id                uuid NOT NULL REFERENCES roleplay.steps(step_id),
      sample_answer_text     text NOT NULL,
      language_code          roleplay.language_code_enum NOT NULL,
      display_order          integer NOT NULL,
      created_at             timestamptz NOT NULL,
      updated_at             timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.roleplay_sessions (
      roleplay_session_id     uuid PRIMARY KEY,
      learner_id               uuid NOT NULL REFERENCES roleplay.users(user_id),
      scenario_version_id       uuid NOT NULL REFERENCES roleplay.scenario_versions(scenario_version_id),
      current_step_id           uuid REFERENCES roleplay.steps(step_id),
      total_chances             integer NOT NULL,
      remaining_chances         integer NOT NULL,
      end_status                roleplay.session_end_status_enum NOT NULL,
      started_at                timestamptz NOT NULL,
      ended_at                  timestamptz,
      created_at                timestamptz NOT NULL,
      updated_at                timestamptz NOT NULL,
      current_step_fail_count   integer NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.roleplay_turns (
      roleplay_turn_id          uuid PRIMARY KEY,
      roleplay_session_id        uuid NOT NULL REFERENCES roleplay.roleplay_sessions(roleplay_session_id),
      step_id                     uuid NOT NULL REFERENCES roleplay.steps(step_id),
      next_step_id                uuid REFERENCES roleplay.steps(step_id),
      turn_order                  integer NOT NULL,
      input_method                 roleplay.input_method_enum NOT NULL,
      remaining_chances_before      integer NOT NULL,
      remaining_chances_after       integer NOT NULL,
      end_status_after              roleplay.session_end_status_enum,
      created_at                    timestamptz NOT NULL,
      fail_count_before              integer NOT NULL,
      fail_count_after               integer NOT NULL
    )
    """,
    # messages.roleplay_turn_id and messages.audio_file_id are plain uuid columns in the
    # ORM (no ForeignKey() declared on either) -- preserved as-is, not invented FKs.
    """
    CREATE TABLE IF NOT EXISTS roleplay.messages (
      message_id                       uuid PRIMARY KEY,
      roleplay_session_id                uuid NOT NULL REFERENCES roleplay.roleplay_sessions(roleplay_session_id),
      roleplay_turn_id                   uuid,
      step_id                             uuid REFERENCES roleplay.steps(step_id),
      scenario_roleplay_character_id     uuid REFERENCES roleplay.scenario_roleplay_characters(scenario_roleplay_character_id),
      message_order                      integer NOT NULL,
      sender_type                         roleplay.sender_type_enum NOT NULL,
      generated_by                        roleplay.message_generated_by_enum,
      message_type                        roleplay.message_type_enum NOT NULL,
      text_content                        text NOT NULL,
      text_language                       roleplay.language_code_enum NOT NULL,
      translation_json                    jsonb,
      audio_file_id                       uuid,
      created_at                          timestamptz NOT NULL,
      hint_level                          varchar
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roleplay.roleplay_evaluations (
      roleplay_evaluation_id     uuid PRIMARY KEY,
      roleplay_turn_id             uuid NOT NULL REFERENCES roleplay.roleplay_turns(roleplay_turn_id),
      roleplay_session_id           uuid NOT NULL REFERENCES roleplay.roleplay_sessions(roleplay_session_id),
      step_id                        uuid NOT NULL REFERENCES roleplay.steps(step_id),
      evaluation_order                integer NOT NULL,
      learner_input_text               text NOT NULL,
      evaluation_result                 roleplay.evaluation_result_enum NOT NULL,
      inferred_intent_text               text,
      step_goal_matched                   boolean,
      evaluation_reason_text              text,
      correction_json                      jsonb,
      cultural_issue_detected               boolean,
      should_advance_step                    boolean NOT NULL,
      should_decrease_chance                  boolean NOT NULL,
      should_end_session                       boolean NOT NULL,
      created_at                                timestamptz NOT NULL
    )
    """,
]

_DOWN_STATEMENTS = [
    "DROP TABLE IF EXISTS roleplay.roleplay_evaluations",
    "DROP TABLE IF EXISTS roleplay.messages",
    "DROP TABLE IF EXISTS roleplay.roleplay_turns",
    "DROP TABLE IF EXISTS roleplay.roleplay_sessions",
    "DROP TABLE IF EXISTS roleplay.step_sample_answers",
    "DROP TABLE IF EXISTS roleplay.steps",
    "DROP TABLE IF EXISTS roleplay.scenario_roleplay_characters",
    "DROP TABLE IF EXISTS roleplay.scenario_locations",
    "DROP TABLE IF EXISTS roleplay.scenario_versions",
    "DROP TABLE IF EXISTS roleplay.scenarios",
    "DROP TABLE IF EXISTS roleplay.roleplay_characters",
    "DROP TABLE IF EXISTS roleplay.roleplay_locations",
    "DROP TABLE IF EXISTS roleplay.file_assets",
    "DROP TABLE IF EXISTS roleplay.users",
    "DROP TYPE IF EXISTS roleplay.evaluation_result_enum",
    "DROP TYPE IF EXISTS roleplay.message_type_enum",
    "DROP TYPE IF EXISTS roleplay.message_generated_by_enum",
    "DROP TYPE IF EXISTS roleplay.sender_type_enum",
    "DROP TYPE IF EXISTS roleplay.input_method_enum",
    "DROP TYPE IF EXISTS roleplay.session_end_status_enum",
    "DROP TYPE IF EXISTS roleplay.difficulty_enum",
    "DROP TYPE IF EXISTS roleplay.scenario_status_enum",
    "DROP TYPE IF EXISTS roleplay.language_code_enum",
    "DROP TYPE IF EXISTS roleplay.user_status_enum",
    "DROP TYPE IF EXISTS roleplay.user_role_enum",
    # Deliberately NOT "DROP SCHEMA roleplay" here: env.py puts Alembic's own
    # alembic_version bookkeeping table inside this schema (version_table_schema),
    # so downgrading this migration must leave the schema itself standing -- Alembic
    # needs it to still exist right after this function returns, to record the
    # downgrade. Dropping the schema self-destructs mid-migration and the whole
    # downgrade rolls back (verified: Postgres DDL is transactional, so this fails
    # safely with zero effect rather than leaving a half-torn-down database -- but it
    # still means "downgrade" silently does nothing, which is the bug being avoided).
]


def upgrade() -> None:
    for statement in _UP_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWN_STATEMENTS:
        op.execute(statement)
