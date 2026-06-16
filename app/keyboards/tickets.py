"""Keyboards and callback data for the ticket flow."""
from collections.abc import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.tickets.prefixes import prefix_name

# Reply-keyboard button captions. Taps arrive as plain text, so handlers match
# these exact strings — keep them in sync with the handlers in coordinator/tickets.
BTN_CHANGE_PREFIX = "🔁 Сменить префикс"
BTN_FINISH = "✅ Завершить"


class TicketConfirmCB(CallbackData, prefix="tickets"):
    action: str  # "confirm" | "cancel"


class TicketPrefixCB(CallbackData, prefix="tpfx"):
    """Prefix the coordinator picks before entering the ticket list."""

    prefix: str


def build_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=TicketConfirmCB(action="confirm"))
    builder.button(text="❌ Отмена", callback_data=TicketConfirmCB(action="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def build_prefix_keyboard(prefixes: Sequence[str]) -> InlineKeyboardMarkup:
    """One button per prefix the coordinator may issue (two per row)."""
    builder = InlineKeyboardBuilder()
    for prefix in prefixes:
        builder.button(
            text=f"{prefix} · {prefix_name(prefix)}",
            callback_data=TicketPrefixCB(prefix=prefix),
        )
    builder.adjust(2)
    return builder.as_markup()


def build_lines_keyboard(can_change_prefix: bool) -> ReplyKeyboardMarkup:
    """Reply keyboard shown while waiting for a list: change prefix / finish.

    A reply keyboard (not inline) so it reads as the current chat actions rather
    than buttons frozen on an old message.
    """
    rows = []
    if can_change_prefix:
        rows.append([KeyboardButton(text=BTN_CHANGE_PREFIX)])
    rows.append([KeyboardButton(text=BTN_FINISH)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Пришлите список…",
    )
