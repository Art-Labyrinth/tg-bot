"""Base class for all ORM models (SQLAlchemy 2.0 style)."""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Every model inherits from this. Alembic discovers tables via Base.metadata."""


class TimestampMixin:
    """Adds created_at / updated_at. Mix into models that need time auditing."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
