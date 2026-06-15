"""Keyboards and callback data for the ticket flow."""
from collections.abc import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.tickets.prefixes import TICKET_TYPE_NAMES


class TicketConfirmCB(CallbackData, prefix="tickets"):
    action: str  # "confirm" | "cancel"


class TicketCategoryCB(CallbackData, prefix="tcat"):
    """Category chosen by a combo coordinator before entering the list."""

    ticket_type: str


def build_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=TicketConfirmCB(action="confirm"))
    builder.button(text="❌ Отмена", callback_data=TicketConfirmCB(action="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def build_category_keyboard(ticket_types: Sequence[str]) -> InlineKeyboardMarkup:
    """One button per ticket type the combo coordinator may issue."""
    builder = InlineKeyboardBuilder()
    for ticket_type in ticket_types:
        builder.button(
            text=TICKET_TYPE_NAMES.get(ticket_type, ticket_type),
            callback_data=TicketCategoryCB(ticket_type=ticket_type),
        )
    builder.adjust(1)
    return builder.as_markup()
