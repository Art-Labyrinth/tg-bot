"""Handler for the /start command."""
from datetime import date

import structlog
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.config import settings
from app.db.models.user import User
from app.i18n import t

router = Router(name="start")
log = structlog.get_logger()

# The festival runs 18–21 June 2026. Show the announcement through its last day,
# then fall back to just the website link.
FESTIVAL_LAST_DAY = date(2026, 6, 21)

# Admin-facing command list (kept in Russian like other admin strings).
ADMIN_MENU = (
    "Команды администратора:\n\n"
    "/users — пользователи (тап по пользователю → назначить роль)\n"
    "<code>/ban &lt;id&gt;</code> — забанить\n"
    "<code>/unban &lt;id&gt;</code> — разбанить\n"
    "/roles — список ролей\n"
    "<code>/setrole &lt;id&gt;</code> — назначить роль кнопками"
)


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    # `user` is injected by UserMiddleware: already loaded/registered and not banned.
    log.info("start_command", telegram_id=user.telegram_id)
    if user.telegram_id == settings.admin_id:
        await message.answer(ADMIN_MENU)
        return
    message_key = "start" if date.today() <= FESTIVAL_LAST_DAY else "after_festival"
    await message.answer(t(message_key, user.locale))
