"""Inline keyboards and callback data for the admin panel."""
from collections.abc import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models.user import User
from app.roles import ROLE_NAMES, Role


class UsersPageCB(CallbackData, prefix="users_page"):
    """Carries the target page index for the users-list pagination buttons."""

    page: int


class UserManageCB(CallbackData, prefix="user_manage"):
    """Tap a user in the list to manage them; page lets us return to the list."""

    telegram_id: int
    page: int


class SetRoleCB(CallbackData, prefix="setrole"):
    """Assign `role` (bitmask value) to user `user_id`."""

    user_id: int
    role: int


# Roles an admin can assign, in button order. Add a role here -> a new button.
ASSIGNABLE_ROLES: tuple[Role, ...] = (
    Role.MASTERS_COORDINATOR,
    Role.VOLUNTEERS_COORDINATOR,
    Role.MASTERS_AND_VOLUNTEERS_COORDINATOR,
    Role.ADMIN,  # reserved: assignable, no extra behaviour wired yet
)


def _pagination_row(page: int, total_pages: int) -> list[InlineKeyboardButton]:
    """Prev / position / next buttons; arrows only when in-bounds."""
    row: list[InlineKeyboardButton] = []
    if page > 0:
        row.append(
            InlineKeyboardButton(text="◀", callback_data=UsersPageCB(page=page - 1).pack())
        )
    row.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}",
            callback_data=UsersPageCB(page=page).pack(),
        )
    )
    if page < total_pages - 1:
        row.append(
            InlineKeyboardButton(text="▶", callback_data=UsersPageCB(page=page + 1).pack())
        )
    return row


def build_users_keyboard(
    users: Sequence[User], page: int, total_pages: int
) -> InlineKeyboardMarkup:
    """One button per user (tap to manage) plus the pagination row."""
    rows: list[list[InlineKeyboardButton]] = []
    for u in users:
        label = ("🚫 " if u.is_banned else "") + (
            u.first_name or (f"@{u.username}" if u.username else str(u.telegram_id))
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=UserManageCB(telegram_id=u.telegram_id, page=page).pack(),
                )
            ]
        )
    rows.append(_pagination_row(page, total_pages))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_role_keyboard(target_id: int, back_to_page: int | None = None) -> InlineKeyboardMarkup:
    """Role buttons + reset for a target user; optional 'back to list' button."""
    builder = InlineKeyboardBuilder()
    for role in ASSIGNABLE_ROLES:
        builder.button(
            text=ROLE_NAMES[role],
            callback_data=SetRoleCB(user_id=target_id, role=int(role)),
        )
    builder.button(
        text="🗑 Сбросить",
        callback_data=SetRoleCB(user_id=target_id, role=int(Role.USER)),
    )
    if back_to_page is not None:
        builder.button(
            text="⬅️ К списку", callback_data=UsersPageCB(page=back_to_page).pack()
        )
    builder.adjust(1)
    return builder.as_markup()
