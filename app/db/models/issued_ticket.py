"""Audit log of tickets issued by coordinators."""
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IssuedTicket(Base):
    __tablename__ = "issued_tickets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ticket_id as returned by the ticket microservice.
    ticket_id: Mapped[str] = mapped_column(String(64), index=True)

    # Who issued it. SET NULL keeps the log if the coordinator is later removed.
    coordinator_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="SET NULL"),
        index=True,
    )

    name: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(254))
    prefix: Mapped[str] = mapped_column(String(8))
    sent_email: Mapped[bool] = mapped_column(default=False, server_default=false())

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<IssuedTicket id={self.id} ticket_id={self.ticket_id!r}>"
