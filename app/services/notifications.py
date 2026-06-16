"""Batched admin notifications about newly registered users.

New users are pushed into a Redis list as they register and a background task
sends one grouped message to the admin. Timing is a *leading-edge throttle*:
the first user is reported immediately, then no further message goes out for at
least NOTIFY_INTERVAL. Users registering inside that cooldown are buffered and
delivered together when it ends; a user arriving after the cooldown has already
elapsed is reported at once.

If a batch exceeds Telegram's message limit, only what fits is sent and the
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
NOTIFY_INTERVAL = 600  # seconds (10 minutes) — minimum gap between messages

_HEADER = "🆕 Новые пользователи:\n\n"
_FOOTER_RESERVE = 60  # room for the "…и ещё N" footer


def _to_text(item: object) -> str:
    """Normalize a Redis list element (bytes/memoryview/str) to text.

    `lpop(key, count)` is typed to return a broad union; we only ever push
    strings, but they come back as `bytes` (unless decode_responses is on),
    so we decode defensively to get a genuine `list[str]`.
    """
    if isinstance(item, str):
        return item
    if isinstance(item, memoryview):
        item = item.tobytes()
    if isinstance(item, (bytes, bytearray)):
        return item.decode()
    return str(item)


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
        # Set whenever a user is queued, so the background loop can sleep until
        # there is actually something to report instead of polling on a timer.
        self._pending = asyncio.Event()

    async def enqueue(
        self, telegram_id: int, username: str | None, first_name: str | None
    ) -> None:
        await self._redis.rpush(QUEUE_KEY, _format_user(telegram_id, username, first_name))
        self._pending.set()

    def signal(self) -> None:
        """Wake the loop without enqueuing (e.g. to drain a leftover queue)."""
        self._pending.set()

    async def wait_for_pending(self) -> None:
        """Block until at least one user has been queued since the last wait."""
        await self._pending.wait()
        self._pending.clear()

    async def flush(self, bot: Bot, admin_id: int) -> bool:
        """Send the queued batch to the admin. Returns True if a message went out."""
        count = await self._redis.llen(QUEUE_KEY)
        if not count:
            return False
        # Atomically take the current batch; anything pushed after stays for next time.
        raw = await self._redis.lpop(QUEUE_KEY, count) or []
        lines: list[str] = [_to_text(item) for item in raw]
        text, shown, dropped = _build_message(lines)

        # Plain text: usernames/names are arbitrary and must not be HTML-parsed.
        try:
            await bot.send_message(admin_id, text, parse_mode=None)
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            await bot.send_message(admin_id, text, parse_mode=None)
        log.info("new_users_notified", shown=shown, dropped=dropped)
        return True


async def run_new_user_notifications(
    notifier: NewUserNotifier, bot: Bot, admin_id: int
) -> None:
    """Background loop: report queued users with a leading-edge throttle.

    The first user goes out immediately; afterwards at least NOTIFY_INTERVAL
    passes before the next message. Users queued during the cooldown are
    batched and delivered when it ends.
    """
    loop = asyncio.get_running_loop()
    # Start "in the past" so the very first user is reported with no delay.
    last_sent = loop.time() - NOTIFY_INTERVAL
    # Pick up anything buffered while the bot was offline.
    notifier.signal()

    while True:
        await notifier.wait_for_pending()
        # Hold off until the cooldown since the previous message has elapsed.
        elapsed = loop.time() - last_sent
        if elapsed < NOTIFY_INTERVAL:
            await asyncio.sleep(NOTIFY_INTERVAL - elapsed)
        try:
            sent = await notifier.flush(bot, admin_id)
        except Exception as exc:  # noqa: BLE001 — keep the loop alive
            log.error("new_user_flush_failed", error=str(exc), exc_info=exc)
            continue
        if sent:
            last_sent = loop.time()
