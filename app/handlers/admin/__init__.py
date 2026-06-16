"""Admin handlers, gated behind IsAdmin at the router level.

The IsAdmin filter is applied once to the whole admin router, so every handler
included here is automatically administrator-only — no per-handler checks.
"""
from aiogram import Router

from app.filters.admin import IsAdmin
from app.handlers.admin import roles, test_tickets, users


def get_admin_router() -> Router:
    router = Router(name="admin")
    # Gate both messages (commands) and callbacks (pagination buttons).
    router.message.filter(IsAdmin())
    router.callback_query.filter(IsAdmin())

    router.include_router(users.router)
    router.include_router(roles.router)
    router.include_router(test_tickets.router)
    return router
