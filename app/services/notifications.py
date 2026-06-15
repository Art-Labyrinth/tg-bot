"""Batched admin notifications about newly registered users.

New users are pushed into a Redis list as they register; a background task
drains the list every few minutes and sends one grouped message to the admin.
If the batch exceeds Telegram's message limit, only what fits is sent and the
rest is dropped.
"""
import asyncio

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from redis.asyncio import Redis

log = structlog.get_logger()

QUEUE_KEY = "new_users:queue"
TELEGRAM_LIMIT = 4096
NOTIFY_INTERVAL = 600  # seconds (10 minutes)

_HEADER = "🆕 Новые пользователи:\n\n"
_FOOTER_RESERVE = 60  # room for the "…и ещё N" footer


def _format_user(telegram_id: int, username: str | None, first_name: str | None) -> str:
    name = first_name or "—"
    handle = f" @{username}" if username else ""
    return f"{telegram_id} · {name}{handle}"


def _build_message(lines: list[str]) -> tuple[str, int, int]:
    """Pack as many lines as fit; returns (text, shown, dropped)."""
    budget = TELEGRAM_LIMIT - len(_HEADER) - _FOOTER_RESERVE
    kept: list[str] = []
    used = 0
    for line in lines:
        if used + len(line) + 1 > budget:
            break
        kept.append(line)
        used += len(line) + 1
    dropped = len(lines) - len(kept)
    text = _HEADER + "\n".join(kept)
    if dropped:
        text += f"\n\n…и ещё {dropped} (не показаны)"
    return text, len(kept), dropped


class NewUserNotifier:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def enqueue(
        self, telegram_id: int, username: str | None, first_name: str | None
    ) -> None:
        await self._redis.rpush(QUEUE_KEY, _format_user(telegram_id, username, first_name))

    async def flush(self, bot: Bot, admin_id: int) -> None:
        count = await self._redis.llen(QUEUE_KEY)
        if not count:
            return
        # Atomically take the current batch; anything pushed after stays for next time.
        raw = await self._redis.lpop(QUEUE_KEY, count) or []
        lines = [item.decode() if isinstance(item, bytes) else item for item in raw]
        text, shown, dropped = _build_message(lines)

        # Plain text: usernames/names are arbitrary and must not be HTML-parsed.
        try:
            await bot.send_message(admin_id, text, parse_mode=None)
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            await bot.send_message(admin_id, text, parse_mode=None)
        log.info("new_users_notified", shown=shown, dropped=dropped)


async def run_new_user_notifications(
    notifier: NewUserNotifier, bot: Bot, admin_id: int
) -> None:
    """Background loop: flush the queue to the admin every NOTIFY_INTERVAL."""
    while True:
        await asyncio.sleep(NOTIFY_INTERVAL)
        try:
            await notifier.flush(bot, admin_id)
        except Exception as exc:  # noqa: BLE001 — keep the loop alive
            log.error("new_user_flush_failed", error=str(exc), exc_info=exc)
