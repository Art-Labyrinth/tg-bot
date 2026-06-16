"""Bitmask role filter.

Gate any handler or router by a required role:

    from app.roles import Role
    from app.filters.role import HasRole

    @router.message(Command("masters"), HasRole(Role.MASTERS_COORDINATOR))
    async def ...:

The filter reads the DB user injected by UserMiddleware (data["user"]), so it
only works on updates that pass through that middleware.
"""
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.db.models.user import User
from app.roles import Role, has_role
from app.tickets.prefixes import available_prefixes


class HasRole(BaseFilter):
    """Pass when the user has ALL bits of `required`."""

    def __init__(self, required: Role) -> None:
        self.required = required

    async def __call__(
        self, event: Message | CallbackQuery, user: User | None = None
    ) -> bool:
        if user is None:
            return False
        return has_role(user.role, self.required)


class HasAnyRole(BaseFilter):
    """Pass when the user has ANY bit of `mask` (e.g. any coordinator role)."""

    def __init__(self, mask: Role) -> None:
        self.mask = mask

    async def __call__(
        self, event: Message | CallbackQuery, user: User | None = None
    ) -> bool:
        if user is None:
            return False
        return bool(Role(user.role) & self.mask)


class IsCoordinator(BaseFilter):
    """Pass for any user who may issue tickets, or for the root admin.

    The root admin (settings.admin_id) is a super-coordinator: they reach the
    ticket flow regardless of their stored role, so the project owner can issue
    any ticket without self-assigning a coordinator role.
    """

    async def __call__(
        self, event: Message | CallbackQuery, user: User | None = None
    ) -> bool:
        if event.from_user is not None and event.from_user.id == settings.admin_id:
            return True
        if user is None:
            return False
        return bool(available_prefixes(user.role))
