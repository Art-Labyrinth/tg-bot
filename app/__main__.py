"""Entry point: python -m app

Starts the asyncio loop and runs the bot. Ctrl+C / SIGTERM from Docker shuts
the process down gracefully via KeyboardInterrupt.
"""
import asyncio

import structlog

from app.bot import run
from app.config import settings
from app.logging_config import setup_logging

log = structlog.get_logger()


def main() -> None:
    setup_logging(debug=settings.debug)

    # Pre-flight: bail out with a clear message if core config is missing, rather
    # than dying with an opaque TelegramUnauthorizedError on the first API call.
    missing = settings.missing_required()
    if missing:
        log.error(
            "missing_required_config",
            missing=missing,
            hint="environment not injected? check the compose .env / CI secrets",
        )
        raise SystemExit(1)

    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
