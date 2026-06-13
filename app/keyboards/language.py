"""Inline keyboard and callback data for the /lang language picker."""
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n import LANGUAGE_NAMES, LOCALES


class LangCB(CallbackData, prefix="lang"):
    """Carries the locale code chosen by the user."""

    code: str


def build_language_keyboard() -> InlineKeyboardMarkup:
    """One button per supported language, native names, one per row."""
    builder = InlineKeyboardBuilder()
    for locale in LOCALES:
        builder.button(text=LANGUAGE_NAMES[locale], callback_data=LangCB(code=locale))
    builder.adjust(1)
    return builder.as_markup()
