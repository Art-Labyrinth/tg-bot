"""Ticket statistics command, available to any administrator.

Unlike the mutating admin commands (root-only, under IsAdmin), /stats is gated by
IsAnyAdmin: the root admin plus any holder of the Administrator role. It only
reads aggregate figures, so it is a safe first capability for that role.

This router is included at the top level (not inside the root-only admin router)
and carries its own IsAnyAdmin filter.
"""
import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.filters.admin import IsAnyAdmin
from app.services.tickets import TicketService, TicketServiceError
from app.tickets.stats_format import format_stats

router = Router(name="admin_stats")
router.message.filter(IsAnyAdmin())
log = structlog.get_logger()


@router.message(Command("stats"))
async def cmd_stats(message: Message, ticket_service: TicketService) -> None:
    try:
        data = await ticket_service.stats()
    except TicketServiceError as exc:
        log.warning("stats_failed", error=str(exc))
        await message.answer("⚠️ Не удалось получить статистику. Попробуйте позже.")
        return

    log.info("stats_requested", telegram_id=message.from_user.id if message.from_user else None)
    try:
        chunks = format_stats(data)
    except Exception as exc:  # noqa: BLE001 — unexpected payload shape must not 500 the update
        log.error("stats_format_failed", error=str(exc), payload=data, exc_info=exc)
        await message.answer("⚠️ Статистика получена, но её не удалось отобразить.")
        return

    for chunk in chunks:
        await message.answer(chunk)
