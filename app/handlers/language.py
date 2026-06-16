"""/lang command — let the user switch the interface language."""
import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.i18n import SUPPORTED_LOCALES, t
from app.keyboards.language import LangCB, build_language_keyboard

router = Router(name="language")
log = structlog.get_logger()


@router.message(Command("lang"))
async def cmd_lang(message: Message, user: User) -> None:
    await message.answer(
        t("lang.prompt", user.locale), reply_markup=build_language_keyboard()
    )


@router.callback_query(LangCB.filter())
async def cb_set_language(
    callback: CallbackQuery,
    callback_data: LangCB,
    session: AsyncSession,
    user: User,
) -> None:
    locale = callback_data.code
    # Guard against codes outside our supported set (e.g. stale buttons).
    if locale not in SUPPORTED_LOCALES:
        await callback.answer()
        return

    await UserRepository(session).set_locale(user.telegram_id, locale)
    await session.commit()
    log.info("locale_changed", telegram_id=user.telegram_id, locale=locale)

    # Confirm in the freshly selected language.
    if isinstance(callback.message, Message):
        await callback.message.edit_text(t("lang.changed", locale))
    await callback.answer()
