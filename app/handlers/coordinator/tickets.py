"""/ticket — coordinators issue tickets from a free-text list.

Flow: /ticket -> send the list -> preview with Confirm/Cancel -> on confirm,
generate via the ticket microservice, log every issued ticket, and post the PNGs
to the chat (email tickets are additionally sent by the service). The parsed
batch lives in FSM data between the list and the confirmation.

Telegram flood limits are handled by retrying sends on TelegramRetryAfter with
the server-provided delay (a back-off queue).
"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InputMediaPhoto,
    MediaUnion,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.repositories.issued_ticket import IssuedTicketRepository
from app.keyboards.tickets import (
    TicketCategoryCB,
    TicketConfirmCB,
    build_category_keyboard,
    build_confirm_keyboard,
)
from app.services.tickets import Ticket, TicketService, TicketServiceError
from app.tickets.models import ParsedBatch, TicketRequest
from app.tickets.parser import parse
from app.tickets.prefixes import available_ticket_types, get_prefix

router = Router(name="coordinator_tickets")
log = structlog.get_logger()

ALBUM_SIZE = 10        # Telegram media group limit

HELP = (
    "Пришли список: одна строка — один билет.\n"
    "• <b>имя</b> → билет в чат\n"
    "• <b>email</b> → билет на почту\n"
    "• <b>имя + email</b> → именной билет на почту\n"
    "• суффикс <code>*N</code> → N копий\n\n"
    "Пример:\n<code>Иван Петров\nivan@mail.com\nМастера *5</code>"
)

T = TypeVar("T")


class TicketFlow(StatesGroup):
    choosing_category = State()
    waiting_lines = State()
    confirming = State()


# --- helpers -----------------------------------------------------------------

async def _flood_safe(call: Callable[[], Awaitable[T]]) -> T:
    """Run a Telegram send, waiting out flood limits instead of failing."""
    while True:
        try:
            return await call()
        except TelegramRetryAfter as exc:
            log.warning("telegram_flood_wait", retry_after=exc.retry_after)
            await asyncio.sleep(exc.retry_after)


def _errors_block(batch: ParsedBatch) -> str:
    return "\n".join(
        f"стр. {e.lineno}: {e.reason} — «{e.text}»" for e in batch.errors
    )


def _preview_text(batch: ParsedBatch) -> str:
    lines = []
    for idx, req in enumerate(batch.requests, start=1):
        who = req.name or "(без имени)"
        mult = f" ×{req.count}" if req.count > 1 else ""
        dest = f"email {req.email}" if req.email else "в чат"
        lines.append(f"{idx}. {who}{mult} → {dest}")
    text = f"Будет создано билетов: <b>{batch.total_tickets}</b>\n\n" + "\n".join(lines)
    if batch.errors:
        text += "\n\n⚠️ Пропущены строки:\n" + _errors_block(batch)
    return text + "\n\nПодтвердить?"


def _to_state(requests: list[TicketRequest]) -> list[dict]:
    return [{"name": r.name, "email": r.email, "count": r.count} for r in requests]


def _from_state(data: list[dict]) -> list[TicketRequest]:
    return [TicketRequest(name=d["name"], email=d["email"], count=d["count"]) for d in data]


# --- handlers ----------------------------------------------------------------

@router.message(Command("ticket"))
async def cmd_ticket(message: Message, user: User, state: FSMContext) -> None:
    types = available_ticket_types(user.role)
    if len(types) == 1:
        await state.update_data(ticket_type=types[0])
        await state.set_state(TicketFlow.waiting_lines)
        await message.answer(HELP)
        return
    # Combo coordinator — pick the category before entering the list.
    await state.set_state(TicketFlow.choosing_category)
    await message.answer(
        "Выберите категорию билетов:", reply_markup=build_category_keyboard(types)
    )


@router.callback_query(TicketFlow.choosing_category, TicketCategoryCB.filter())
async def on_category(
    callback: CallbackQuery,
    callback_data: TicketCategoryCB,
    user: User,
    state: FSMContext,
) -> None:
    if callback_data.ticket_type not in available_ticket_types(user.role):
        await callback.answer("Недоступная категория.", show_alert=True)
        return
    await state.update_data(ticket_type=callback_data.ticket_type)
    await state.set_state(TicketFlow.waiting_lines)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(HELP)
    await callback.answer()


@router.message(TicketFlow.waiting_lines, F.text)
async def receive_lines(message: Message, state: FSMContext) -> None:
    batch = parse(message.text or "")
    if not batch.requests:
        await message.answer(
            "Не нашёл ни одной валидной строки.\n\n" + _errors_block(batch)
        )
        return
    await state.update_data(requests=_to_state(batch.requests))
    await state.set_state(TicketFlow.confirming)
    await message.answer(_preview_text(batch), reply_markup=build_confirm_keyboard())


@router.callback_query(TicketFlow.confirming, TicketConfirmCB.filter(F.action == "cancel"))
async def on_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.edit_text("Отменено.")
    await callback.answer()


@router.callback_query(TicketFlow.confirming, TicketConfirmCB.filter(F.action == "confirm"))
async def on_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    bot: Bot,
    session: AsyncSession,
    ticket_service: TicketService,
) -> None:
    message = callback.message
    if message is None:
        # The originating message is gone (too old) — can't post tickets back.
        await callback.answer("Сообщение недоступно, начните заново.", show_alert=True)
        return

    data = await state.get_data()
    requests = _from_state(data["requests"])
    prefix = get_prefix(data["ticket_type"])
    await state.clear()
    await callback.answer()

    status = message if isinstance(message, Message) else None
    if status is not None:
        await status.edit_text("Генерирую билеты…")

    await _generate_and_send(
        bot=bot,
        chat_id=message.chat.id,
        service=ticket_service,
        session=session,
        coordinator_id=user.telegram_id,
        requests=requests,
        prefix=prefix,
        lang=user.locale,
        status=status,
    )


async def _generate_and_send(
    *,
    bot: Bot,
    chat_id: int,
    service: TicketService,
    session: AsyncSession,
    coordinator_id: int,
    requests: list[TicketRequest],
    prefix: str,
    lang: str,
    status: Message | None,
) -> None:
    total = sum(r.count for r in requests)
    tickets: list[Ticket] = []
    failures: list[str] = []
    log_repo = IssuedTicketRepository(session)
    done = 0

    for req in requests:
        for _ in range(req.count):
            try:
                if req.email:
                    ticket = await service.email(
                        email=req.email, name=req.name, prefix=prefix, lang=lang
                    )
                else:
                    ticket = await service.create(name=req.name, prefix=prefix)
            except TicketServiceError as exc:
                failures.append(f"{req.name or req.email}: {exc}")
                done += 1
                continue
            tickets.append(ticket)
            log_repo.record(
                ticket_id=ticket.ticket_id,
                coordinator_id=coordinator_id,
                name=req.name,
                email=req.email,
                prefix=prefix,
                sent_email=req.email is not None,
            )
            done += 1
        if status is not None:
            try:
                await status.edit_text(f"Генерирую билеты… {done}/{total}")
            except Exception:  # noqa: BLE001 — progress edit is best-effort
                pass

    # Persist the audit log before posting, so issuance is recorded even if a
    # later Telegram send fails.
    await session.commit()

    await _send_albums(bot, chat_id, tickets)

    report = f"✅ Готово: {len(tickets)}/{total}."
    if failures:
        report += "\n❌ Ошибки:\n" + "\n".join(failures[:20])
    await _flood_safe(lambda: bot.send_message(chat_id, report))
    log.info("tickets_issued", coordinator_id=coordinator_id, made=len(tickets), failed=len(failures))


async def _send_albums(bot: Bot, chat_id: int, tickets: list[Ticket]) -> None:
    """Post tickets to the chat as PNGs, grouped into albums of 10."""
    for start in range(0, len(tickets), ALBUM_SIZE):
        chunk = tickets[start : start + ALBUM_SIZE]
        if len(chunk) == 1:
            ticket = chunk[0]
            await _flood_safe(
                lambda t=ticket: bot.send_photo(
                    chat_id,
                    BufferedInputFile(t.image_png, filename=f"{t.ticket_id}.png"),
                    caption=t.ticket_id,
                )
            )
        else:
            # Declare the wider element type so the list is `list[MediaUnion]`
            # (list is invariant — a `list[InputMediaPhoto]` won't satisfy it).
            media: list[MediaUnion] = [
                InputMediaPhoto(
                    media=BufferedInputFile(t.image_png, filename=f"{t.ticket_id}.png"),
                    caption=t.ticket_id,
                )
                for t in chunk
            ]
            await _flood_safe(lambda m=media: bot.send_media_group(chat_id, m))
