"""Admin-only test ticket generation.

Issues N nameless, email-less tickets under the TEST prefix by submitting a
normal TicketJob to the shared worker — so test runs inherit the same queueing,
rate-limiting, progress and audit logging as real issuance.
"""
import structlog
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.db.models.user import User
from app.services.ticket_queue import TicketJob, TicketWorker
from app.tickets.models import TicketRequest

router = Router(name="admin_test_tickets")
log = structlog.get_logger()

TEST_PREFIX = "TEST"
MAX_TEST = 50  # guard against accidentally flooding the ticket service


@router.message(Command("testtickets"))
async def cmd_test_tickets(
    message: Message,
    command: CommandObject,
    user: User,
    ticket_worker: TicketWorker,
) -> None:
    arg = (command.args or "").strip()
    if not arg.isdigit() or int(arg) < 1:
        await message.answer("Использование: <code>/testtickets &lt;кол-во&gt;</code>")
        return
    count = int(arg)
    if count > MAX_TEST:
        await message.answer(f"Максимум за раз: {MAX_TEST}.")
        return

    job = TicketJob(
        chat_id=message.chat.id,
        coordinator_id=user.telegram_id,
        prefix=TEST_PREFIX,
        lang=user.locale,
        requests=[TicketRequest(name=None, email=None, count=count)],
    )
    ahead = ticket_worker.submit(job)
    log.info("test_tickets_requested", admin_id=user.telegram_id, count=count)
    if ahead == 0:
        await message.answer(f"▶️ Генерирую тестовых билетов ({TEST_PREFIX}): {count}…")
    else:
        await message.answer(
            f"⏳ {count} тестовых билетов в очереди. Перед вами: {ahead}."
        )
