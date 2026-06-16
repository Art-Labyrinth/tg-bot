"""/ticket — coordinators issue tickets from a free-text list.

Flow: /ticket -> pick a prefix -> send the list -> preview with Confirm/Cancel.
On confirm the batch is handed to the TicketWorker, which generates tickets via
the microservice one at a time (rate-limited), logs each issued ticket and posts
the PNGs to the chat. Submitting a new list while one is running just queues it.

The parsed batch lives in FSM data between the list and the confirmation.
"""
import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.config import settings
from app.db.models.user import User
from app.keyboards.tickets import (
    BTN_CHANGE_PREFIX,
    BTN_FINISH,
    TicketConfirmCB,
    TicketPrefixCB,
    build_confirm_keyboard,
    build_lines_keyboard,
    build_prefix_keyboard,
)
from app.services.ticket_queue import TicketJob, TicketWorker
from app.tickets.models import ParsedBatch, TicketRequest
from app.tickets.parser import parse
from app.tickets.prefixes import ALL_PREFIXES, available_prefixes, prefix_name

router = Router(name="coordinator_tickets")
log = structlog.get_logger()

HELP = (
    "Пришли список: одна строка — один билет.\n"
    "• <b>имя</b> → билет в чат\n"
    "• <b>email</b> → билет на почту\n"
    "• <b>имя + email</b> → именной билет на почту\n"
    "• суффикс <code>*N</code> → N копий\n\n"
    "Пример:\n<code>Иван Петров\nivan@mail.com\nМастера *5</code>"
)


class TicketFlow(StatesGroup):
    choosing_prefix = State()
    waiting_lines = State()
    confirming = State()


# --- helpers -----------------------------------------------------------------

def _prefixes_for(user: User) -> tuple[str, ...]:
    """Prefixes this user may issue; the root admin may issue any."""
    if user.telegram_id == settings.admin_id:
        return ALL_PREFIXES
    return available_prefixes(user.role)


def _can_change_prefix(user: User) -> bool:
    """True if the user has more than one prefix to switch between."""
    return len(_prefixes_for(user)) > 1


# Hint shown when the coordinator can keep sending more lists.
NEXT_HINT = "Пришлите следующий список или завершите. 👇"


def _errors_block(batch: ParsedBatch) -> str:
    return "\n".join(
        f"стр. {e.lineno}: {e.reason} — «{e.text}»" for e in batch.errors
    )


def _preview_text(batch: ParsedBatch, prefix: str) -> str:
    lines = []
    for idx, req in enumerate(batch.requests, start=1):
        who = req.name or "(без имени)"
        mult = f" ×{req.count}" if req.count > 1 else ""
        dest = f"email {req.email}" if req.email else "в чат"
        lines.append(f"{idx}. {who}{mult} → {dest}")
    text = (
        f"Префикс: <b>{prefix} · {prefix_name(prefix)}</b>\n"
        f"Будет создано билетов: <b>{batch.total_tickets}</b>\n\n" + "\n".join(lines)
    )
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
    prefixes = _prefixes_for(user)
    if not prefixes:
        await message.answer("У вас нет прав на выдачу билетов.")
        return
    if len(prefixes) == 1:
        # Single-role coordinator — prefix is fixed, go straight to the list.
        await state.update_data(prefix=prefixes[0])
        await state.set_state(TicketFlow.waiting_lines)
        await message.answer(HELP, reply_markup=build_lines_keyboard(can_change_prefix=False))
        return
    # Combo coordinator — choose the prefix before entering the list.
    await state.set_state(TicketFlow.choosing_prefix)
    await message.answer(
        "Выберите префикс билета:", reply_markup=build_prefix_keyboard(prefixes)
    )


@router.callback_query(TicketFlow.choosing_prefix, TicketPrefixCB.filter())
async def on_prefix(
    callback: CallbackQuery,
    callback_data: TicketPrefixCB,
    user: User,
    state: FSMContext,
) -> None:
    if callback_data.prefix not in _prefixes_for(user):
        await callback.answer("Недоступный префикс.", show_alert=True)
        return
    await state.update_data(prefix=callback_data.prefix)
    await state.set_state(TicketFlow.waiting_lines)
    if isinstance(callback.message, Message):
        # The inline picker can't carry a reply keyboard, so confirm the choice
        # on it and send the list prompt with the reply keyboard separately.
        await callback.message.edit_text(
            f"Префикс: <b>{callback_data.prefix} · {prefix_name(callback_data.prefix)}</b>"
        )
        await callback.message.answer(
            HELP, reply_markup=build_lines_keyboard(_can_change_prefix(user))
        )
    await callback.answer()


# Reply-keyboard controls. Registered before receive_lines and matched by exact
# text so a tap is never mistaken for a list. State-agnostic: the reply keyboard
# can linger across states, so the buttons must work wherever they appear.

@router.message(F.text == BTN_FINISH)
async def on_finish(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Готово. /ticket — начать заново.", reply_markup=ReplyKeyboardRemove()
    )


@router.message(F.text == BTN_CHANGE_PREFIX)
async def on_change_prefix(message: Message, user: User, state: FSMContext) -> None:
    prefixes = _prefixes_for(user)
    if len(prefixes) <= 1:
        await message.answer("Доступен только один префикс.")
        return
    await state.set_state(TicketFlow.choosing_prefix)
    await message.answer(
        "Выберите префикс билета:", reply_markup=build_prefix_keyboard(prefixes)
    )


@router.message(TicketFlow.waiting_lines, F.text)
async def receive_lines(message: Message, state: FSMContext) -> None:
    batch = parse(message.text or "")
    if not batch.requests:
        await message.answer(
            "Не нашёл ни одной валидной строки.\n\n" + _errors_block(batch)
        )
        return
    data = await state.get_data()
    await state.update_data(requests=_to_state(batch.requests))
    await state.set_state(TicketFlow.confirming)
    await message.answer(
        _preview_text(batch, data["prefix"]), reply_markup=build_confirm_keyboard()
    )


@router.callback_query(TicketFlow.confirming, TicketConfirmCB.filter(F.action == "cancel"))
async def on_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    # Drop this batch but keep the coordinator in the flow (same prefix). The
    # reply keyboard is still at the bottom, so no markup is needed here.
    await state.set_state(TicketFlow.waiting_lines)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("Список отменён. " + NEXT_HINT)
    await callback.answer()


@router.callback_query(TicketFlow.confirming, TicketConfirmCB.filter(F.action == "confirm"))
async def on_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    ticket_worker: TicketWorker,
) -> None:
    message = callback.message
    if message is None:
        await callback.answer("Сообщение недоступно, начните заново.", show_alert=True)
        return

    data = await state.get_data()
    job = TicketJob(
        chat_id=message.chat.id,
        coordinator_id=user.telegram_id,
        prefix=data["prefix"],
        lang=user.locale,
        requests=_from_state(data["requests"]),
    )
    # Keep the coordinator in the flow with the same prefix: they can paste the
    # next list straight away, no /ticket and no prefix pick. Only "Завершить"
    # (or /start) clears the state.
    await state.set_state(TicketFlow.waiting_lines)
    await callback.answer()

    # Hand off to the serial worker; it owns generation, logging and posting.
    ahead = ticket_worker.submit(job)
    if ahead == 0:
        note = "▶️ Принято, начинаю генерацию…"
    else:
        note = f"⏳ Принято. В очереди перед вами: {ahead}."
    if isinstance(message, Message):
        # No markup here: edit_text only takes inline; the reply keyboard set
        # when the flow started stays at the bottom of the chat.
        await message.edit_text(f"{note}\n\n{NEXT_HINT}")
