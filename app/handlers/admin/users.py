"""Admin commands for managing users.

  /users [query]          — paginated list, optional case-insensitive name search
  /ban <telegram_id>      — ban a user
  /unban <telegram_id>    — unban a user

Pagination keeps the active search query in FSM data (`users_filter`), so the
prev/next buttons only need to carry the page number (see keyboards/admin.py).
"""
from math import ceil

import structlog
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.repositories.user import UserRepository
from app.keyboards.admin import UsersPageCB, build_users_pagination

router = Router(name="admin_users")
log = structlog.get_logger()

PAGE_SIZE = 10


def _format_users_page(
    users, page: int, total_pages: int, total: int, query: str | None
) -> str:
    header = f"Пользователи ({total})"
    if query:
        header += f' — поиск: "{query}"'
    header += f"\nСтраница {page + 1}/{total_pages}\n"

    if not users:
        return header + "\nНичего не найдено."

    lines = []
    for u in users:
        name = u.first_name or "—"
        username = f"@{u.username}" if u.username else "—"
        role = u.role.name if u.role else "—"
        flags = " 🚫" if u.is_banned else ""
        lines.append(f"{u.telegram_id} | {name} | {username} | {role}{flags}")
    return header + "\n" + "\n".join(lines)


async def _render_users(
    session: AsyncSession, *, page: int, query: str | None
) -> tuple[str, InlineKeyboardMarkup]:
    repo = UserRepository(session)
    users, total = await repo.list_page(
        offset=page * PAGE_SIZE, limit=PAGE_SIZE, name_query=query
    )
    total_pages = max(1, ceil(total / PAGE_SIZE))
    text = _format_users_page(users, page, total_pages, total, query)
    keyboard = build_users_pagination(page, total_pages)
    return text, keyboard


@router.message(Command("users"))
async def cmd_users(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    query = command.args.strip() if command.args else None
    # Remember the active search so pagination buttons can reuse it.
    await state.update_data(users_filter=query)
    text, keyboard = await _render_users(session, page=0, query=query)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(UsersPageCB.filter())
async def cb_users_page(
    callback: CallbackQuery,
    callback_data: UsersPageCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    query = data.get("users_filter")
    text, keyboard = await _render_users(session, page=callback_data.page, query=query)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


def _parse_target_id(args: str | None) -> int | None:
    if args and args.strip().lstrip("-").isdigit():
        return int(args.strip())
    return None


@router.message(Command("ban"))
async def cmd_ban(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    target_id = _parse_target_id(command.args)
    if target_id is None:
        await message.answer("Использование: /ban <telegram_id>")
        return
    if target_id == settings.admin_id:
        await message.answer("Нельзя забанить главного администратора.")
        return

    user = await UserRepository(session).set_banned(target_id, True)
    if user is None:
        await message.answer(f"Пользователь {target_id} не найден.")
        return
    await session.commit()
    log.info("user_banned", telegram_id=target_id)
    await message.answer(f"Пользователь {target_id} забанен. 🚫")


@router.message(Command("unban"))
async def cmd_unban(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    target_id = _parse_target_id(command.args)
    if target_id is None:
        await message.answer("Использование: /unban <telegram_id>")
        return

    user = await UserRepository(session).set_banned(target_id, False)
    if user is None:
        await message.answer(f"Пользователь {target_id} не найден.")
        return
    await session.commit()
    log.info("user_unbanned", telegram_id=target_id)
    await message.answer(f"Пользователь {target_id} разбанен.")
