"""Admin commands for user roles (hardcoded bitmask, see app/roles.py).

  /roles                 — list the available roles
  /setrole <telegram_id> — show role buttons for that user; tapping one assigns it
"""
import structlog
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.user import UserRepository
from app.keyboards.admin import SetRoleCB, build_role_keyboard
from app.roles import ROLE_NAMES, Role, role_label

router = Router(name="admin_roles")
log = structlog.get_logger()


@router.message(Command("roles"))
async def cmd_roles(message: Message) -> None:
    lines = [f"• {name}" for name in ROLE_NAMES.values()]
    await message.answer(
        "Роли:\n"
        + "\n".join(lines)
        + "\n\nНазначить: <code>/setrole &lt;telegram_id&gt;</code>"
    )


@router.message(Command("setrole"))
async def cmd_setrole(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    args = (command.args or "").strip()
    if not args.lstrip("-").isdigit():
        await message.answer("Использование: <code>/setrole &lt;telegram_id&gt;</code>")
        return

    target_id = int(args)
    user = await UserRepository(session).get(target_id)
    if user is None:
        await message.answer(f"Пользователь {target_id} не найден.")
        return

    await message.answer(
        f"Роль для {target_id} (сейчас: {role_label(user.role)}):",
        reply_markup=build_role_keyboard(target_id),
    )


@router.callback_query(SetRoleCB.filter())
async def cb_set_role(
    callback: CallbackQuery, callback_data: SetRoleCB, session: AsyncSession
) -> None:
    role = Role(callback_data.role)
    user = await UserRepository(session).set_role(callback_data.user_id, role)
    if user is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    await session.commit()
    log.info("role_assigned", telegram_id=callback_data.user_id, role=int(role))
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"Пользователю {callback_data.user_id} назначена роль: {role_label(role)}."
        )
    await callback.answer()
