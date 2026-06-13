"""Assemble and run the bot: wire config, Redis, DB and routers together."""
import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.db.session import create_engine, create_session_factory
from app.handlers import get_main_router
from app.middlewares.database import DatabaseMiddleware
from app.middlewares.user import UserMiddleware
from app.services.redis import create_redis, create_storage

log = structlog.get_logger()


async def run() -> None:
    # --- Infrastructure ---
    redis = create_redis()
    storage = create_storage(redis)
    engine = create_engine()
    session_factory = create_session_factory(engine)

    # --- Bot & Dispatcher ---
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Middleware order matters: the first registered is the outermost.
    # DatabaseMiddleware (provides the session) must wrap UserMiddleware
    # (which uses that session to load/register the user and check bans).
    db_mw = DatabaseMiddleware(session_factory)
    user_mw = UserMiddleware()
    for observer in (dp.message, dp.callback_query):
        observer.middleware(db_mw)
        observer.middleware(user_mw)

    dp.include_router(get_main_router())

    # --- Go ---
    try:
        log.info("bot_starting")
        # Drop updates accumulated while the bot was offline instead of replaying them.
        # await bot.delete_webhook(drop_pending_updates=True)
        await bot.send_message(settings.admin_id, "Bot starting")
        await dp.start_polling(bot)
    finally:
        log.info("bot_stopping")
        await bot.session.close()
        await redis.aclose()
        await engine.dispose()
