"""Repository for the user audit log.

Keep all writes to user_history behind this repository so future triggers
(send failures, cron reconciliation) record events in one consistent way.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_history import UserEvent, UserHistory


class UserHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def record(
        self,
        user_id: int,
        event: UserEvent,
        data: dict,
    ) -> UserHistory:
        """Stage a history entry. The caller owns the transaction (commit)."""
        entry = UserHistory(user_id=user_id, event=event, data=data)
        self.session.add(entry)
        return entry
