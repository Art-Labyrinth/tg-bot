"""Inline keyboards and callback data for the admin panel."""
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class UsersPageCB(CallbackData, prefix="users_page"):
    """Carries the target page index for the users-list pagination buttons."""

    page: int


def build_users_pagination(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Prev / position / next navigation row for the paginated users list.

    Arrows appear only when there is somewhere to go, so the admin can't
    paginate past the bounds. The middle button is just a position indicator;
    it points back to the current page, so tapping it is a no-op.
    """
    row: list[InlineKeyboardButton] = []
    if page > 0:
        row.append(
            InlineKeyboardButton(
                text="◀", callback_data=UsersPageCB(page=page - 1).pack()
            )
        )
    row.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}",
            callback_data=UsersPageCB(page=page).pack(),
        )
    )
    if page < total_pages - 1:
        row.append(
            InlineKeyboardButton(
                text="▶", callback_data=UsersPageCB(page=page + 1).pack()
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[row])
