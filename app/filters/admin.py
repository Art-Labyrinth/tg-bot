"""Access filter for administrator-only handlers.

Applied at the admin router level, so every admin handler is gated in one place.
Currently grants access only to the root administrator from settings. To add
role-based admins later, extend __call__ to also check the user's role.
"""
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.config import get_settings


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if event.from_user is None:
            return False
        return event.from_user.id == get_settings().admin_id
