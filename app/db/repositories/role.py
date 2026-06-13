"""Role repository — all SQL against the `roles` catalog."""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.role import Role


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> Sequence[Role]:
        result = await self.session.scalars(select(Role).order_by(Role.name))
        return result.all()

    async def get_by_name(self, name: str) -> Role | None:
        return await self.session.scalar(select(Role).where(Role.name == name))

    async def create(self, name: str, description: str | None = None) -> Role:
        """Stage a new role. Caller owns the transaction (commit)."""
        role = Role(name=name, description=description)
        self.session.add(role)
        await self.session.flush()
        return role
