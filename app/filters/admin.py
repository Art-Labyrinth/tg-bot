"""Access filters for administrator handlers.

IsAdmin gates the mutating admin commands (users / roles / ban / ticket issuing)
and grants access only to the root administrator from settings.

IsAnyAdmin is broader: it also lets holders of the Administrator role through.
It backs read-only admin features (currently /stats), so the reserved role gets
a first, low-risk capability without being able to change anything.
"""
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.db.models.user import User
from app.roles import Role


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if event.from_user is None:
            return False
        return event.from_user.id == settings.admin_id


class IsAnyAdmin(BaseFilter):
    """Pass for the root admin or any holder of the Administrator role."""

    async def __call__(
        self, event: Message | CallbackQuery, user: User | None = None
    ) -> bool:
        if event.from_user is not None and event.from_user.id == settings.admin_id:
            return True
        if user is None:
            return False
        return Role.ADMIN in Role(user.role)
