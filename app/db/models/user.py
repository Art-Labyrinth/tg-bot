"""Telegram user model."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.role import Role


class User(Base, TimestampMixin):
    __tablename__ = "users"

    # telegram_id is the user's id from Telegram. It can be large, hence BigInteger,
    # and it is unique and present in every update, so we use it as the primary key.
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    username: Mapped[str | None] = mapped_column(String(32))
    first_name: Mapped[str | None] = mapped_column(String(64))
    # Raw language_code as reported by Telegram (kept for reference/history).
    language_code: Mapped[str | None] = mapped_column(String(8))
    # Our normalized UI locale (one of i18n.SUPPORTED_LOCALES). Drives
    # localization; derived from language_code at registration, defaults to "en".
    locale: Mapped[str] = mapped_column(String(8), default="en", server_default="en")

    # Checked in middleware: banned users never reach the handlers.
    is_banned: Mapped[bool] = mapped_column(default=False, server_default=false())

    # One role per user; NULL means "no special role". Eager-loaded (joined) so
    # handlers can read user.role without a separate async lazy-load.
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL")
    )
    role: Mapped["Role | None"] = relationship(lazy="joined")

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} username={self.username!r}>"
