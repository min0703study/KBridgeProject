from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.app.core.config import get_settings
from backend.app.db import models  # noqa: F401 -- registers all tables on Base.metadata
from backend.app.db.base import ROLEPLAY_SCHEMA, Base

# These module-level statements are only valid when executed by the Alembic CLI.
# Guard everything that touches `context` behind a runtime check so that a plain
# `import backend.app.db.migrations.env` (e.g. from a test) does not crash.

target_metadata = Base.metadata

# All app tables live under the `roleplay` schema (see base.py) -- keep Alembic's own
# bookkeeping table there too, instead of polluting `public` (which the K-Bridge admin
# hub's schema.sql also owns on the same shared `kBridge` database). `include_schemas`
# is required for autogenerate/`alembic check` to reflect non-`public` schemas at all --
# without it, autogenerate reports every roleplay.* table as "new" on every run because
# its reflection defaults to `public` only.
#
# `include_schemas=True` alone reflects and diffs EVERY schema in the connected database,
# not just `roleplay` -- on the real shared `kBridge` instance, that includes the hub's
# own `public.users` / `public.scenarios` / etc. Since target_metadata only knows about
# `roleplay.*` tables, autogenerate/`alembic check` would otherwise conclude those
# unrelated hub tables aren't in the model and propose `op.drop_table(...)` for every one
# of them -- confirmed by reproduction: `alembic revision --autogenerate` against a DB
# seeded with public.users/public.scenarios/public.students generated exactly that. The
# `include_name` filter below is required to scope schema comparison to `roleplay` only
# (Alembic's own documented "multiple schemas" recipe) -- do not remove it.
def _include_name(name: str | None, type_: str, parent_names: dict) -> bool:
    if type_ == "schema":
        return name == ROLEPLAY_SCHEMA
    return True


_CONFIGURE_KWARGS = {
    "version_table_schema": ROLEPLAY_SCHEMA,
    "include_schemas": True,
    "include_name": _include_name,
}


def _running_under_alembic() -> bool:
    """Return True only when Alembic's runtime context is active."""
    try:
        context.is_offline_mode()
        return True
    except Exception:
        return False


def _database_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_CONFIGURE_KWARGS,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, **_CONFIGURE_KWARGS)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    cfg = context.config
    section = cfg.get_section(cfg.config_ini_section) or {}
    section["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        # version_table_schema=ROLEPLAY_SCHEMA means Alembic writes its own bookkeeping
        # table (alembic_version) into `roleplay`, not `public` -- but on a brand-new
        # database that schema doesn't exist yet (migration 0001 is what creates it), so
        # Alembic can't even record "0001 ran" without it existing first. Bootstrap the
        # schema here, outside of migration tracking, before configuring the version
        # table. Idempotent -- a no-op on every later run.
        from sqlalchemy import text

        await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {ROLEPLAY_SCHEMA}"))
        await connection.commit()
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


if _running_under_alembic():
    _config = context.config
    if _config.config_file_name is not None:
        fileConfig(_config.config_file_name)

    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())
