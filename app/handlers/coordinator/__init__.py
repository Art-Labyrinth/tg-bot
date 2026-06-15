"""Coordinator handlers, gated by any coordinator role at the router level."""
from aiogram import Router

from app.filters.role import HasAnyRole
from app.handlers.coordinator import tickets
from app.roles import Role

_COORDINATOR_ROLES = Role.MASTERS_COORDINATOR | Role.VOLUNTEERS_COORDINATOR


def get_coordinator_router() -> Router:
    router = Router(name="coordinator")
    gate = HasAnyRole(_COORDINATOR_ROLES)
    router.message.filter(gate)
    router.callback_query.filter(gate)
    router.include_router(tickets.router)
    return router
