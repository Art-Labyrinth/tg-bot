"""Alembic environment (async).

The URL comes from the application settings, and target_metadata comes from
Base, so autogeneration sees every model. That's why the models must be
imported (app.db.models imports them all).
"""
import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.db.base import Base
import app.db.models  # noqa: F401  (registers models on Base.metadata)

config = context.config
target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """Render custom TypeDecorators (e.g. RoleType) as their DB-level impl type.

    Otherwise autogenerate emits `app.roles.RoleType()`, which migrations can't
    import. At the DB level these are just their underlying type, so render that.
    """
    from sqlalchemy.types import TypeDecorator

    if type_ == "type" and isinstance(obj, TypeDecorator):
        impl = obj.impl
        impl_cls = impl if isinstance(impl, type) else impl.__class__
        return f"sa.{impl_cls.__name__}()"
    return False  # fall back to default rendering


def run_migrations_offline() -> None:
    context.configure(
        url=settings.postgres_dsn,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(settings.postgres_dsn)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
