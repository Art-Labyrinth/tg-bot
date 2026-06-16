"""Per-user command menu shown on /start and pushed on role assignment.

A non-root user may hold a coordinator role, the Administrator role, both, or
neither. We compose the relevant command blocks so the menu always matches what
the user can actually do — and a single source of truth keeps /start and the
role-grant notification in sync.
"""
from app.handlers.coordinator.menu import coordinator_menu, is_coordinator
from app.roles import Role

STATS_MENU = "Команды администратора:\n\n/stats — статистика по билетам."


def has_admin_role(role: int) -> bool:
    """True if the user holds the Administrator role (grants /stats)."""
    return Role.ADMIN in Role(role)


def account_menu(role: int) -> str | None:
    """Combined command list for a non-root user, or None if they have none."""
    parts: list[str] = []
    if is_coordinator(role):
        parts.append(coordinator_menu(role))
    if has_admin_role(role):
        parts.append(STATS_MENU)
    return "\n\n".join(parts) if parts else None
