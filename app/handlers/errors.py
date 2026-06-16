"""Global error handler.

Logs unhandled errors and replies to the user neutrally, so a failure in a
handler never surfaces as a bare stack trace. Benign "message is not modified"
errors (e.g. tapping the page-indicator button) are swallowed silently.
"""
import structlog
from aiogram import Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, ErrorEvent

log = structlog.get_logger()


async def _safe_answer(callback: CallbackQuery, text: str | None = None) -> None:
    try:
        await callback.answer(text)
    except TelegramBadRequest:
        pass


async def on_error(event: ErrorEvent) -> bool:
    exc = event.exception
    update = event.update

    # Benign: editing a message to identical content/markup. Nothing changed.
    if isinstance(exc, TelegramBadRequest) and "message is not modified" in str(exc):
        if update.callback_query is not None:
            await _safe_answer(update.callback_query)
        return True

    log.error("update_error", update_id=update.update_id, error=str(exc), exc_info=exc)

    if update.callback_query is not None:
        await _safe_answer(update.callback_query, "Что-то пошло не так.")
    elif update.message is not None:
        try:
            await update.message.answer("Что-то пошло не так. Попробуйте ещё раз.")
        except TelegramBadRequest:
            pass
    return True


def register_errors(dp: Dispatcher) -> None:
    dp.errors.register(on_error)
