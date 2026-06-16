"""Serial background worker that turns ticket batches into issued tickets.

Coordinators submit a batch (a prefix plus parsed lines); the worker processes
one batch at a time, so the ticket microservice -- which sends emails -- is
never hit concurrently and stays within its rate limit. A coordinator who
submits another batch while one is running simply lands behind it in the queue.

Within a batch the worker waits SEND_DELAY between microservice calls and
refreshes a progress message no more often than every PROGRESS_INTERVAL seconds.
"""
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import BufferedInputFile, InputMediaPhoto, MediaUnion, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.issued_ticket import IssuedTicketRepository
from app.services.tickets import Ticket, TicketService, TicketServiceError
from app.tickets.models import TicketRequest

log = structlog.get_logger()

ALBUM_SIZE = 10          # Telegram media group limit
SEND_DELAY = 1.0         # seconds between microservice calls (the service emails)
PROGRESS_INTERVAL = 5.0  # min seconds between progress-message edits

T = TypeVar("T")


@dataclass(slots=True)
class TicketJob:
    """One submitted batch: a prefix and the lines to issue under it."""

    chat_id: int
    coordinator_id: int
    prefix: str
    lang: str
    requests: list[TicketRequest]

    @property
    def total(self) -> int:
        return sum(r.count for r in self.requests)


class TicketWorker:
    def __init__(
        self,
        bot: Bot,
        service: TicketService,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._bot = bot
        self._service = service
        self._session_factory = session_factory
        self._queue: asyncio.Queue[TicketJob] = asyncio.Queue()
        self._current: TicketJob | None = None

    def submit(self, job: TicketJob) -> int:
        """Queue a batch; return how many batches are ahead of it (0 = starts now)."""
        ahead = self._queue.qsize() + (1 if self._current is not None else 0)
        self._queue.put_nowait(job)
        return ahead

    async def run(self) -> None:
        """Drain the queue forever, one batch at a time."""
        while True:
            job = await self._queue.get()
            self._current = job
            try:
                await self._process(job)
            except Exception as exc:  # noqa: BLE001 — one bad batch must not kill the worker
                log.error(
                    "ticket_batch_failed",
                    coordinator_id=job.coordinator_id,
                    error=str(exc),
                    exc_info=exc,
                )
                await self._send(job.chat_id, "❌ Не удалось обработать список. Попробуйте ещё раз.")
            finally:
                self._current = None
                self._queue.task_done()

    async def _process(self, job: TicketJob) -> None:
        total = job.total
        loop = asyncio.get_running_loop()
        status = await self._send(job.chat_id, f"▶️ Генерирую билеты {job.prefix}: 0/{total}…")

        tickets: list[Ticket] = []
        failures: list[str] = []
        done = 0
        last_progress = loop.time()

        async with self._session_factory() as session:
            log_repo = IssuedTicketRepository(session)
            for req in job.requests:
                for _ in range(req.count):
                    try:
                        if req.email:
                            ticket = await self._service.email(
                                email=req.email, name=req.name, prefix=job.prefix, lang=job.lang
                            )
                        else:
                            ticket = await self._service.create(name=req.name, prefix=job.prefix)
                    except TicketServiceError as exc:
                        failures.append(f"{req.name or req.email}: {exc}")
                        done += 1
                        await asyncio.sleep(SEND_DELAY)
                        continue

                    tickets.append(ticket)
                    log_repo.record(
                        ticket_id=ticket.ticket_id,
                        coordinator_id=job.coordinator_id,
                        name=req.name,
                        email=req.email,
                        prefix=job.prefix,
                        sent_email=req.email is not None,
                    )
                    done += 1

                    # Refresh progress at most every PROGRESS_INTERVAL seconds.
                    now = loop.time()
                    if status is not None and now - last_progress >= PROGRESS_INTERVAL:
                        last_progress = now
                        await self._edit(status, f"▶️ Генерирую билеты {job.prefix}: {done}/{total}…")
                    # Space out service calls so we don't overrun the email sender.
                    await asyncio.sleep(SEND_DELAY)

            # Persist the audit log before posting, so issuance is recorded even
            # if a later Telegram send fails.
            await session.commit()

        await self._send_albums(job.chat_id, tickets)

        report = f"✅ Готово ({job.prefix}): {len(tickets)}/{total}."
        if failures:
            report += "\n❌ Ошибки:\n" + "\n".join(failures[:20])
        if status is not None:
            await self._edit(status, report)
        else:
            await self._send(job.chat_id, report)
        log.info(
            "tickets_issued",
            coordinator_id=job.coordinator_id,
            prefix=job.prefix,
            made=len(tickets),
            failed=len(failures),
        )

    # --- Telegram helpers ----------------------------------------------------

    async def _send(self, chat_id: int, text: str) -> Message | None:
        try:
            return await self._flood_safe(lambda: self._bot.send_message(chat_id, text))
        except Exception as exc:  # noqa: BLE001 — status messages are best-effort
            log.warning("ticket_status_send_failed", error=str(exc))
            return None

    async def _edit(self, message: Message, text: str) -> None:
        try:
            await self._flood_safe(lambda: message.edit_text(text))
        except Exception:  # noqa: BLE001 — progress edit is best-effort
            pass

    async def _send_albums(self, chat_id: int, tickets: list[Ticket]) -> None:
        """Post tickets to the chat as PNGs, grouped into albums of 10."""
        for start in range(0, len(tickets), ALBUM_SIZE):
            chunk = tickets[start : start + ALBUM_SIZE]
            if len(chunk) == 1:
                ticket = chunk[0]
                await self._flood_safe(
                    lambda t=ticket: self._bot.send_photo(
                        chat_id,
                        BufferedInputFile(t.image_png, filename=f"{t.ticket_id}.png"),
                        caption=t.ticket_id,
                    )
                )
            else:
                media: list[MediaUnion] = [
                    InputMediaPhoto(
                        media=BufferedInputFile(t.image_png, filename=f"{t.ticket_id}.png"),
                        caption=t.ticket_id,
                    )
                    for t in chunk
                ]
                await self._flood_safe(lambda m=media: self._bot.send_media_group(chat_id, m))

    @staticmethod
    async def _flood_safe(call: Callable[[], Awaitable[T]]) -> T:
        """Run a Telegram send, waiting out flood limits instead of failing."""
        while True:
            try:
                return await call()
            except TelegramRetryAfter as exc:
                log.warning("telegram_flood_wait", retry_after=exc.retry_after)
                await asyncio.sleep(exc.retry_after)
