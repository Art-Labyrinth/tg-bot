#!/bin/sh
# Container entrypoint: apply migrations, then start the bot.
#
# `set -e` aborts if the migration step fails, so the bot never starts against
# an out-of-date schema. `exec` replaces the shell with the bot process so it
# becomes PID 1 and receives SIGTERM/SIGINT directly for a clean shutdown.
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting bot..."
exec python -m app
