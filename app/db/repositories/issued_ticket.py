"""Repository for the issued-tickets audit log."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.issued_ticket import IssuedTicket


class IssuedTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def record(
        self,
        *,
        ticket_id: str,
        coordinator_id: int | None,
        name: str | None,
        email: str | None,
        prefix: str,
        sent_email: bool,
    ) -> IssuedTicket:
        """Stage a log entry. The caller owns the transaction (commit)."""
        entry = IssuedTicket(
            ticket_id=ticket_id,
            coordinator_id=coordinator_id,
            name=name,
            email=email,
            prefix=prefix,
            sent_email=sent_email,
        )
        self.session.add(entry)
        return entry
