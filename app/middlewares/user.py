"""Middleware that loads (or registers) the user and enforces bans.

Runs on every message and callback, after DatabaseMiddleware (so a session is
available under data["session"]). It guarantees two things for every handler:

  * data["user"] is a persisted User row (existing or freshly registered);
  * banned users are dropped here and never reach the handlers.

aiogram already resolves the Telegram user into data["event_from_user"], so we
read it from there instead of digging into the raw event.
"""
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser

from app.db.repositories.user import UserRepository
from app.services.notifications import NewUserNotifier

log = structlog.get_logger()


class UserMiddleware(BaseMiddleware):
    def __init__(self, notifier: NewUserNotifier) -> None:
        self._notifier = notifier

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        # No user behind the update (e.g. channel posts) — nothing to load.
        if tg_user is None:
            return await handler(event, data)

        session = data["session"]
        users = UserRepository(session)
        user, created = await users.get_or_create(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            language_code=tg_user.language_code,
        )
        # Persist registration (and its audit entry) before the handler runs,
        # so a new user is recorded even if the handler later fails.
        await session.commit()

        if created:
            # Queue an admin notification; never let it break update handling.
            try:
                await self._notifier.enqueue(
                    user.telegram_id, user.username, user.first_name
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("notify_enqueue_failed", error=str(exc))

        if user.is_banned:
            log.info("dropped_banned_user", telegram_id=user.telegram_id)
            return None  # short-circuit: the handler never sees this update

        data["user"] = user
        return await handler(event, data)
