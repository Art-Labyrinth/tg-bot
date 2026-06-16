"""User roles as a hardcoded bitmask.

Roles are behavior (who may do what), so they live in code as a single source of
truth; the database stores only the integer value on the user. Single roles are
powers of two, so a user can hold several at once, and a composite like
"Masters and Volunteers Coordinator" is literally the bitwise OR of the two.
"""
import enum

from sqlalchemy import Integer
from sqlalchemy.types import TypeDecorator


class Role(enum.IntFlag):
    USER = 0                                # default, no special permissions
    MASTERS_COORDINATOR = enum.auto()       # 1
    VOLUNTEERS_COORDINATOR = enum.auto()    # 2
    ADMIN = enum.auto()                     # 4 (reserved, not used yet)

    # Named composite (alias) — equals MASTERS_COORDINATOR | VOLUNTEERS_COORDINATOR.
    MASTERS_AND_VOLUNTEERS_COORDINATOR = MASTERS_COORDINATOR | VOLUNTEERS_COORDINATOR

    # Mask of every single-bit role; used to validate incoming values.
    ANY = MASTERS_COORDINATOR | VOLUNTEERS_COORDINATOR | ADMIN


# Human-readable names (admin-facing, kept in Russian like other admin strings).
ROLE_NAMES: dict[Role, str] = {
    Role.USER: "Пользователь",
    Role.MASTERS_COORDINATOR: "Координатор Мастеров",
    Role.VOLUNTEERS_COORDINATOR: "Координатор Волонтёров",
    Role.MASTERS_AND_VOLUNTEERS_COORDINATOR: "Координатор Мастеров и Волонтёров",
    Role.ADMIN: "Администратор",
}


def has_role(value: int, required: Role) -> bool:
    """True if `value` contains every bit of `required` (USER/0 is always met)."""
    return (Role(value) & required) == required


def role_label(value: int) -> str:
    """Display name for a role value, including unnamed bit combinations."""
    role = Role(value)
    if role in ROLE_NAMES:
        return ROLE_NAMES[role]
    parts = [
        ROLE_NAMES[single]
        for single in (
            Role.MASTERS_COORDINATOR,
            Role.VOLUNTEERS_COORDINATOR,
            Role.ADMIN,
        )
        if single in role
    ]
    return ", ".join(parts) if parts else ROLE_NAMES[Role.USER]


class RoleType(TypeDecorator):
    """Stores a Role as a plain integer, returns a Role on load."""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Role | int | None, dialect) -> int | None:
        return int(value) if value is not None else None

    def process_result_value(self, value: int | None, dialect) -> Role | None:
        return Role(value) if value is not None else None
