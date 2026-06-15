"""Combine all feature routers into one.

Each feature lives in its own module with its own Router. To add a feature,
import its router and include it here. The main router attaches to the Dispatcher.
"""
from aiogram import Router

from app.handlers import echo, language, start
from app.handlers.admin import get_admin_router
from app.handlers.coordinator import get_coordinator_router


def get_main_router() -> Router:
    router = Router(name="main")
    # Order matters: an update flows through routers top-down until one matches.
    # echo catches any text, so it is ALWAYS last.
    router.include_router(start.router)
    router.include_router(language.router)
    router.include_router(get_admin_router())
    router.include_router(get_coordinator_router())
    router.include_router(echo.router)
    return router
