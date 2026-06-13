"""Message catalog and the translate helper.

Each entry maps a key to its translations. Use t(key, locale) to fetch a string;
missing translations fall back to DEFAULT_LOCALE, then to the key itself, so a
forgotten translation degrades gracefully instead of crashing.

Texts may contain {placeholders}; format them at the call site, e.g.
    t("start", user.locale).format(name=user.first_name)
"""
from app.i18n.locale import DEFAULT_LOCALE, Locale

MESSAGES: dict[str, dict[Locale, str]] = {
    "start": {
        Locale.ru: (
            "Привет, {name}! 👋\n"
            "Я пока умею немного, но скоро научусь общаться по-настоящему.\n\n"
            "Сменить язык: /lang"
        ),
        Locale.en: (
            "Hi, {name}! 👋\n"
            "I can't do much yet, but soon I'll learn to really chat.\n\n"
            "Change language: /lang"
        ),
        Locale.ro: (
            "Salut, {name}! 👋\n"
            "Deocamdată pot puține, dar în curând voi învăța să conversez cu adevărat.\n\n"
            "Schimbă limba: /lang"
        ),
    },
    "lang.prompt": {
        Locale.ru: "Выберите язык:",
        Locale.en: "Choose your language:",
        Locale.ro: "Alege limba:",
    },
    "lang.changed": {
        Locale.ru: "Язык переключён на русский. ✅",
        Locale.en: "Language switched to English. ✅",
        Locale.ro: "Limba a fost schimbată în română. ✅",
    },
}


def t(key: str, locale: str) -> str:
    """Return the localized string for `key` in `locale`.

    `locale` may be a Locale or a plain string from the DB (StrEnum keys match
    plain strings). Falls back to the default locale, then to the key.
    """
    entry = MESSAGES.get(key, {})
    return entry.get(locale) or entry.get(DEFAULT_LOCALE) or key  # type: ignore[arg-type]
