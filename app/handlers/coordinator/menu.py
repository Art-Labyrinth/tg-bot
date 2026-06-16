"""Coordinator-facing command menu.

Shown on /start to a coordinator and pushed to a user the moment an admin grants
them a coordinator role. Built from `available_prefixes`, so "who is a
coordinator" and "what they may issue" share a single source of truth.
"""
from app.tickets.prefixes import available_prefixes


def is_coordinator(role: int) -> bool:
    """True if the user may issue at least one ticket prefix."""
    return bool(available_prefixes(role))


def coordinator_menu(role: int) -> str:
    """Command list for a coordinator.

    Single-role coordinators always issue under their one fixed prefix and never
    pick one, so prefixes are not mentioned to them. The combo coordinator picks
    a prefix from the inline buttons /ticket shows.
    """
    if len(available_prefixes(role)) > 1:
        ticket = (
            "/ticket — выдать билеты: выберите префикс кнопкой, "
            "затем пришлите список (одна строка — один билет)."
        )
    else:
        ticket = "/ticket — выдать билеты: пришлите список (одна строка — один билет)."
    return "Команды координатора:\n\n" + ticket
