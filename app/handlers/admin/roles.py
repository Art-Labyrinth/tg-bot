"""Admin commands for the roles catalog.

  /roles                       — list all roles
  /addrole <name> [description] — add a new role
  /setrole <telegram_id> <name> — assign a role to a user
"""
import structlog
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.role import RoleRepository
from app.db.repositories.user import UserRepository

router = Router(name="admin_roles")
log = structlog.get_logger()


@router.message(Command("roles"))
async def cmd_roles(message: Message, session: AsyncSession) -> None:
    roles = await RoleRepository(session).list_all()
    if not roles:
        await message.answer("Ролей пока нет. Добавь: /addrole <name> [description]")
        return
    lines = [
        f"• {r.name}" + (f" — {r.description}" if r.description else "")
        for r in roles
    ]
    await message.answer("Роли:\n" + "\n".join(lines))


@router.message(Command("addrole"))
async def cmd_addrole(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    parts = (command.args or "").split(maxsplit=1)
    if not parts or not parts[0]:
        await message.answer("Использование: /addrole <name> [description]")
        return
    name = parts[0].strip()
    description = parts[1].strip() if len(parts) > 1 else None

    repo = RoleRepository(session)
    if await repo.get_by_name(name) is not None:
        await message.answer(f"Роль «{name}» уже существует.")
        return

    role = await repo.create(name, description)
    await session.commit()
    log.info("role_created", role_id=role.id, name=role.name)
    await message.answer(f"Роль «{name}» создана.")


@router.message(Command("setrole"))
async def cmd_setrole(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[0].lstrip("-").isdigit():
        await message.answer("Использование: /setrole <telegram_id> <role_name>")
        return
    target_id = int(parts[0])
    role_name = parts[1].strip()

    role = await RoleRepository(session).get_by_name(role_name)
    if role is None:
        await message.answer(f"Роль «{role_name}» не найдена.")
        return

    user = await UserRepository(session).set_role(target_id, role.id)
    if user is None:
        await message.answer(f"Пользователь {target_id} не найден.")
        return

    await session.commit()
    log.info("role_assigned", telegram_id=target_id, role=role_name)
    await message.answer(f"Пользователю {target_id} назначена роль «{role_name}».")
