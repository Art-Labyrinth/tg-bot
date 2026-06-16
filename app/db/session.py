"""SQLAlchemy async session factory.

The engine is created once per process. Sessions are short-lived: one per
incoming Telegram update (opened by app/middlewares/database.py).
"""
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.postgres_dsn,
        echo=settings.debug,   # log SQL statements in DEBUG mode
        pool_pre_ping=True,    # check the connection is alive before handing it out
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        engine,
        expire_on_commit=False,  # keep objects usable after commit
    )
