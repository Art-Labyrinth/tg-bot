"""Lightweight dict-based localization."""
from app.i18n.locale import (
    DEFAULT_LOCALE,
    LANGUAGE_NAMES,
    LOCALES,
    SUPPORTED_LOCALES,
    Locale,
    resolve_locale,
)
from app.i18n.messages import t

__all__ = [
    "Locale",
    "LOCALES",
    "SUPPORTED_LOCALES",
    "DEFAULT_LOCALE",
    "LANGUAGE_NAMES",
    "resolve_locale",
    "t",
]
