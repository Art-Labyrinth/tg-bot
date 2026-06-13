"""Entry point: python -m app

Starts the asyncio loop and runs the bot. Ctrl+C / SIGTERM from Docker shuts
the process down gracefully via KeyboardInterrupt.
"""
import asyncio

from app.bot import run
from app.config import get_settings
from app.logging_config import setup_logging


def main() -> None:
    settings = get_settings()
    setup_logging(debug=settings.debug)
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
