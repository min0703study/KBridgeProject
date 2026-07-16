from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# All roleplay tables/enums live in their own PostgreSQL schema, not `public`.
# The shared DB (`kBridge`) also backs the K-Bridge admin hub, whose own
# schema.sql defines unrelated `public.users` / `public.scenarios` tables --
# without this, table names collide across the two apps on the same instance.
ROLEPLAY_SCHEMA = "roleplay"


class Base(DeclarativeBase):
    metadata = MetaData(schema=ROLEPLAY_SCHEMA)
