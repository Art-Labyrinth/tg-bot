"""Ticket type prefixes and the role -> ticket type mapping.

Provisional: the microservice will own the prefix table later. The role mapping
decides which ticket type a coordinator may issue (category from role).
"""
from app.roles import Role

_PREFIXES = {
    "basic": "GST",
    "guest": "GST",
    "master": "MST",
    "volunteer": "VLR",
    "organizer": "ORG",
    "family": "FML",
    "friends": "FRD",
    "discounted": "DSC",
    "cash": "CSH",
}


def get_prefix(ticket_type: str) -> str:
    """Prefix for a ticket type (defaults to GST for unknown types)."""
    return _PREFIXES.get(ticket_type.lower(), "GST")


# Which ticket type each coordinator role issues. The "master" ticket covers
# masters, musicians, specialists and hosts; "volunteer" covers volunteers.
ROLE_TICKET_TYPE: dict[Role, str] = {
    Role.MASTERS_COORDINATOR: "master",
    Role.VOLUNTEERS_COORDINATOR: "volunteer",
}

# Human-readable category names (for the combo coordinator's category picker).
TICKET_TYPE_NAMES: dict[str, str] = {
    "master": "Мастеров",
    "volunteer": "Волонтёров",
}


def available_ticket_types(role: int) -> list[str]:
    """Every ticket type the role may issue (one for a single role, several for combo)."""
    current = Role(role)
    return [t for bit, t in ROLE_TICKET_TYPE.items() if bit in current]


def ticket_type_for_role(role: int) -> str | None:
    """The single ticket type a coordinator may issue, or None if ambiguous/none.

    None means the combo coordinator (several types) — the caller asks them to pick.
    """
    types = available_ticket_types(role)
    return types[0] if len(types) == 1 else None
