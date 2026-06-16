"""Parse a coordinator's free-text ticket list.

Grammar — one line per ticket, every part optional except that a line must have
a name or an email:

    [name words] [email] [*N]

  * email     — a token containing "@" (validated); routes the ticket to email.
  * *N / xN   — explicit multiplier suffix => N copies. Explicit on purpose, so
                "Команда 2" stays a name while "Команда *2" means two tickets.
  * the rest  — the name.

No email -> the ticket is returned in chat. The function does no I/O, so it is
trivially unit-testable.
"""
import re

from app.tickets.models import LineError, ParsedBatch, TicketRequest

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COUNT_RE = re.compile(r"^[*xX×](\d+)$")
MAX_COUNT_PER_LINE = 50


def parse(text: str) -> ParsedBatch:
    requests: list[TicketRequest] = []
    errors: list[LineError] = []

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        email: str | None = None
        count = 1
        count_seen = False
        name_parts: list[str] = []
        problem: str | None = None

        for token in line.split():
            multiplier = COUNT_RE.match(token)
            if multiplier:
                if count_seen:
                    problem = "несколько множителей"
                    break
                count = int(multiplier.group(1))
                count_seen = True
                continue
            if "@" in token:
                if email is not None:
                    problem = "несколько email в строке"
                    break
                if not EMAIL_RE.match(token):
                    problem = f"неверный email: {token}"
                    break
                email = token
                continue
            name_parts.append(token)

        if problem is not None:
            errors.append(LineError(lineno, line, problem))
            continue
        if not (1 <= count <= MAX_COUNT_PER_LINE):
            errors.append(LineError(lineno, line, f"количество должно быть 1..{MAX_COUNT_PER_LINE}"))
            continue

        name = " ".join(name_parts) or None
        if name is None and email is None:
            errors.append(LineError(lineno, line, "нет ни имени, ни email"))
            continue

        requests.append(TicketRequest(name=name, email=email, count=count))

    return ParsedBatch(requests=requests, errors=errors)
