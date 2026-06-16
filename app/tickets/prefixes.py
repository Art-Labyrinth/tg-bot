"""Ticket prefixes and which ones each coordinator role may issue.

Provisional: the microservice will own the prefix table later. A single-role
coordinator issues exactly one prefix; the combo coordinator (holding both the
Masters and Volunteers roles) may issue any prefix.
"""
from app.roles import Role

# Every ticket prefix with its admin-facing name, in display order.
PREFIX_NAMES: dict[str, str] = {
    "GST": "Guest",
    "MST": "Master",
    "VLR": "Volunteer",
    "ORG": "Orgs",
    "FML": "Family",
    "FRD": "Friends",
    "CSH": "Cash",
    "DSC": "Discount",
}
ALL_PREFIXES: tuple[str, ...] = tuple(PREFIX_NAMES)

# The single prefix each individual coordinator role may issue.
ROLE_PREFIX: dict[Role, str] = {
    Role.MASTERS_COORDINATOR: "MST",
    Role.VOLUNTEERS_COORDINATOR: "VLR",
}


def available_prefixes(role: int) -> tuple[str, ...]:
    """Prefixes a coordinator may issue.

    The combo coordinator (both Masters and Volunteers) may issue any prefix;
    a single-role coordinator is limited to their own.
    """
    current = Role(role)
    if Role.MASTERS_COORDINATOR in current and Role.VOLUNTEERS_COORDINATOR in current:
        return ALL_PREFIXES
    return tuple(prefix for bit, prefix in ROLE_PREFIX.items() if bit in current)


def prefix_name(prefix: str) -> str:
    """Admin-facing name for a prefix (falls back to the code itself)."""
    return PREFIX_NAMES.get(prefix, prefix)
