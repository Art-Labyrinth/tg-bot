"""Assemble and run the bot: wire config, Redis, DB and routers together."""
import asyncio
import contextlib

import httpx
import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.db.session import create_engine, create_session_factory
from app.handlers import get_main_router
from app.handlers.errors import register_errors
from app.middlewares.database import DatabaseMiddleware
from app.middlewares.user import UserMiddleware
from app.services.notifications import NewUserNotifier, run_new_user_notifications
from app.services.redis import create_redis, create_storage
from app.services.ticket_queue import TicketWorker
from app.services.tickets import TicketService

log = structlog.get_logger()


async def run() -> None:
    # --- Infrastructure ---
    redis = create_redis()
    storage = create_storage(redis)
    engine = create_engine()
    session_factory = create_session_factory(engine)
    http_client = httpx.AsyncClient(timeout=30.0)
    ticket_service = TicketService(
        settings.ticket_service, http_client, settings.bot_api_secret.get_secret_value()
    )
    notifier = NewUserNotifier(redis)

    # --- Bot & Dispatcher ---
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)
    # App-wide singletons injected into handlers by name (e.g. `ticket_worker`).
    ticket_worker = TicketWorker(bot, ticket_service, session_factory)
    dp["ticket_worker"] = ticket_worker

    # These run as OUTER middleware (before filtering) so router-level filters
    # like IsCoordinator/HasRole can read data["user"]; an inner middleware would
    # only run after a handler matched, leaving those filters with user=None.
    # Order matters: the first registered is the outermost. DatabaseMiddleware
    # (provides the session) must wrap UserMiddleware (which uses that session to
    # load/register the user and check bans).
    db_mw = DatabaseMiddleware(session_factory)
    user_mw = UserMiddleware(notifier)
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(db_mw)
        observer.outer_middleware(user_mw)

    dp.include_router(get_main_router())
    register_errors(dp)

    # Background tasks: the serial ticket worker and batched new-user notifications.
    worker_task = asyncio.create_task(ticket_worker.run())
    notify_task = asyncio.create_task(
        run_new_user_notifications(notifier, bot, settings.admin_id)
    )

    # --- Go ---
    try:
        log.info("bot_starting")
        # Drop updates accumulated while the bot was offline instead of replaying them.
        # await bot.delete_webhook(drop_pending_updates=True)
        await bot.send_message(settings.admin_id, "Bot starting")
        await dp.start_polling(bot)
    finally:
        log.info("bot_stopping")
        notify_task.cancel()
        worker_task.cancel()
        for task in (notify_task, worker_task):
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await bot.session.close()
        await redis.aclose()
        await engine.dispose()
        await http_client.aclose()
