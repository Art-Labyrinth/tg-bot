"""Data structures produced by the ticket line parser."""
from dataclasses import dataclass


@dataclass(slots=True)
class TicketRequest:
    """One parsed ticket line: a name and/or an email, plus how many copies."""

    name: str | None
    email: str | None
    count: int  # >= 1

    @property
    def to_email(self) -> bool:
        return self.email is not None


@dataclass(slots=True)
class LineError:
    """A line that could not be parsed, kept for the preview feedback."""

    lineno: int
    text: str
    reason: str


@dataclass(slots=True)
class ParsedBatch:
    requests: list[TicketRequest]
    errors: list[LineError]

    @property
    def total_tickets(self) -> int:
        return sum(r.count for r in self.requests)
