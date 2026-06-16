"""Supported locales and the rules for resolving them.

Adding a language later means: add a member here, add its native name to
LANGUAGE_NAMES, and add its column to the message catalog in messages.py.
"""
import enum


class Locale(enum.StrEnum):
    ru = "ru"
    en = "en"
    ro = "ro"


# Display order (used for the /lang keyboard). frozenset for fast membership.
LOCALES: tuple[Locale, ...] = (Locale.ru, Locale.en, Locale.ro)
SUPPORTED_LOCALES: frozenset[Locale] = frozenset(LOCALES)
DEFAULT_LOCALE: Locale = Locale.en

# Native language names for buttons.
LANGUAGE_NAMES: dict[Locale, str] = {
    Locale.ru: "🇷🇺 Русский",
    Locale.en: "🇬🇧 English",
    Locale.ro: "🇷🇴 Română",
}


def resolve_locale(telegram_language_code: str | None) -> Locale:
    """Map Telegram's language_code to one of our supported locales.

    Telegram may send tags like "en", "ru", "en-US", "pt-br". We match on the
    primary subtag (the part before "-"), case-insensitively. Anything we don't
    support falls back to DEFAULT_LOCALE.
    """
    if telegram_language_code:
        primary = telegram_language_code.split("-", 1)[0].lower()
        if primary in SUPPORTED_LOCALES:
            return Locale(primary)
    return DEFAULT_LOCALE
