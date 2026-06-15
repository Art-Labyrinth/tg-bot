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
            "<b>18–21 июня 2026</b>\n"
            "15-й фестиваль Art Labyrinth\n"
            "<i>Art-Labyrinth · Pulse of the Earth</i>\n\n"
            "#экологичность #вегетарианство #альтернативная_культура #творчество "
            "#самовыражение #музыка #осознанность #комьюнити #без_алкоголя "
            "#ненасилие #уважение\n\n"
            "📍 Сокола, Шолданешты\n"
            "📞 +37367496787"
        ),
        Locale.en: (
            "<b>18–21 June 2026</b>\n"
            "15th Art Labyrinth festival\n"
            "<i>Art-Labyrinth · Pulse of the Earth</i>\n\n"
            "#sustainability #vegetarianism #alternative_culture #creativity "
            "#self_expression #music #mindfulness #community #alcohol_free "
            "#nonviolence #respect\n\n"
            "📍 Socola, Șoldănești\n"
            "📞 +37367496787"
        ),
        Locale.ro: (
            "<b>18–21 iunie 2026</b>\n"
            "Al 15-lea festival Art Labyrinth\n"
            "<i>Art-Labyrinth · Pulse of the Earth</i>\n\n"
            "#sustenabilitate #vegetarianism #cultură_alternativă #creativitate "
            "#auto_exprimare #muzică #mindfulness #comunitate #fără_alcool "
            "#nonviolență #respect\n\n"
            "📍 Socola, Șoldănești\n"
            "📞 +37367496787"
        ),
    },
    # Shown after the festival ends — just point to the website.
    "after_festival": {
        Locale.ru: (
            "ℹ️ Подробная информация о фестивале Art Labyrinth — на сайте:\n"
            "https://fest.art-labyrinth.org/"
        ),
        Locale.en: (
            "ℹ️ Full information about the Art Labyrinth festival is on the site:\n"
            "https://fest.art-labyrinth.org/"
        ),
        Locale.ro: (
            "ℹ️ Informații complete despre festivalul Art Labyrinth — pe site:\n"
            "https://fest.art-labyrinth.org/"
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
