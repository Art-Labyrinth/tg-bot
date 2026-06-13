"""Append-only audit log of user-related events.

Each row is an immutable record: what happened, when, and a snapshot of the
relevant user data at that moment. The `users` table holds the current state;
this table holds the history of how it got there.

Events are written by deliberate triggers (registration, and later: send
failures, cron reconciliation, ...), NOT on every incoming message.
"""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserEvent(enum.StrEnum):
    """Kinds of events recorded in the history table.

    Stored as a plain string column, so adding new event kinds here does not
    require a database migration.
    """

    registration = "registration"
    data_change = "data_change"


class UserHistory(Base):
    __tablename__ = "user_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
    )

    event: Mapped[str] = mapped_column(String(32))

    # Snapshot of the user data relevant to this event (e.g. profile fields at
    # registration time). JSONB keeps it queryable on the Postgres side.
    data: Mapped[dict] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<UserHistory id={self.id} user_id={self.user_id} event={self.event!r}>"
