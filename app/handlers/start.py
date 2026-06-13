"""Handler for the /start command."""
import structlog
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db.models.user import User
from app.i18n import t

router = Router(name="start")
log = structlog.get_logger()


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    # `user` is injected by UserMiddleware: already loaded/registered and not banned.
    log.info("start_command", telegram_id=user.telegram_id)
    await message.answer(t("start", user.locale).format(name=user.first_name))
