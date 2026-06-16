"""Coordinator handlers, gated by ticket-issuing access at the router level."""
from aiogram import Router

from app.filters.role import IsCoordinator
from app.handlers.coordinator import tickets


def get_coordinator_router() -> Router:
    router = Router(name="coordinator")
    # Any coordinator role OR the root admin (see IsCoordinator).
    gate = IsCoordinator()
    router.message.filter(gate)
    router.callback_query.filter(gate)
    router.include_router(tickets.router)
    return router
