"""User repository — the single place where SQL against `users` lives.

The repository pattern isolates data access: handlers and middleware call
readable methods (get, get_or_create) and know nothing about SQLAlchemy.
"""
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.models.user_history import UserEvent
from app.db.repositories.user_history import UserHistoryRepository
from app.i18n import resolve_locale


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.history = UserHistoryRepository(session)

    async def get(self, telegram_id: int) -> User | None:
        return await self.session.get(User, telegram_id)

    async def get_or_create(
        self,
        telegram_id: int,
        *,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
    ) -> User:
        """Return the existing user, or create and register a new one.

        Policy: an existing user is returned untouched — profile fields coming
        from Telegram are NOT overwritten here. Keeping the data fresh is handled
        elsewhere (see the user_history audit flow), not on the hot path.

        For a brand-new user we also record a `registration` event in the audit
        log with a snapshot of the data at sign-up time.

        Does not commit — the caller owns the transaction.
        """
        user = await self.session.get(User, telegram_id)
        if user is not None:
            return user

        # Normalize Telegram's language_code to one of our supported locales.
        locale = resolve_locale(language_code)
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language_code=language_code,
            locale=locale,
        )
        self.session.add(user)
        # Flush so the users row exists before the history FK references it.
        await self.session.flush()

        self.history.record(
            user_id=telegram_id,
            event=UserEvent.registration,
            data={
                "username": username,
                "first_name": first_name,
                "language_code": language_code,
                "locale": locale,
            },
        )
        await self.session.flush()
        return user

    async def list_page(
        self,
        *,
        offset: int,
        limit: int,
        name_query: str | None = None,
    ) -> tuple[Sequence[User], int]:
        """Return one page of users plus the total count (for pagination).

        When name_query is given, filters by a case-insensitive substring of
        first_name OR username.
        """
        condition = None
        if name_query:
            pattern = f"%{name_query}%"
            condition = or_(
                User.first_name.ilike(pattern),
                User.username.ilike(pattern),
            )

        stmt = select(User)
        count_stmt = select(func.count()).select_from(User)
        if condition is not None:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
        users = (await self.session.scalars(stmt)).all()
        total = await self.session.scalar(count_stmt) or 0
        return users, total

    async def set_banned(self, telegram_id: int, banned: bool) -> User | None:
        """Toggle the ban flag. Returns None if the user does not exist."""
        user = await self.session.get(User, telegram_id)
        if user is not None:
            user.is_banned = banned
        return user

    async def set_role(self, telegram_id: int, role_id: int | None) -> User | None:
        """Assign a role (or None to clear). Returns None if the user is absent."""
        user = await self.session.get(User, telegram_id)
        if user is not None:
            user.role_id = role_id
        return user

    async def set_locale(self, telegram_id: int, locale: str) -> User | None:
        """Set the user's UI locale. Returns None if the user does not exist."""
        user = await self.session.get(User, telegram_id)
        if user is not None:
            user.locale = locale
        return user
