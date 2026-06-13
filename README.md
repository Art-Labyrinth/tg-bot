# tg-bot

A Telegram bot built on **aiogram 3**, designed to grow into an AI assistant.
Stack: Python 3.13, aiogram, PostgreSQL, Redis, Docker.

## Architecture

```
app/
├── __main__.py          # entry point: python -m app
├── bot.py               # builds Bot + Dispatcher, registers middleware and routers
├── config.py            # settings from env (pydantic-settings) + DSN
├── logging_config.py    # structlog: colored output in DEBUG, JSON in prod
├── handlers/            # bot features, each one its own Router
│   ├── __init__.py      #   combines all routers into one
│   ├── start.py         #   /start — greeting (user already loaded by middleware)
│   ├── echo.py          #   echo — future entry point into the AI conversation
│   └── admin/           #   admin-only handlers (gated by IsAdmin at router level)
├── middlewares/
│   ├── database.py      # opens a DB session for each update
│   └── user.py          # loads/registers the user, checks ban, injects into handlers
├── filters/
│   └── admin.py         # IsAdmin access filter
├── keyboards/
│   └── admin.py         # inline keyboards + callback data for the admin panel
├── services/
│   └── redis.py         # Redis client + FSM storage (dialog state)
└── db/
    ├── base.py          # DeclarativeBase + TimestampMixin
    ├── session.py       # async engine and session factory
    ├── models/          # ORM models (User, UserHistory, Role)
    └── repositories/    # DB queries (repository pattern)
migrations/              # Alembic (async)
```

### How it scales

- **New feature** = a new module in `handlers/` with its own `Router`, included in `handlers/__init__.py`. The rest of the code stays untouched.
- **New table** = a model in `db/models/`, re-exported in `db/models/__init__.py`, then autogenerate a migration.
- **DB queries** live in `db/repositories/`, not scattered across handlers.
- **AI layer** later: create `services/ai.py`, call it from `handlers/echo.py`, keep the dialog context in FSM (Redis is already wired up).

## Running

```bash
cp .env.example .env          # fill in BOT_TOKEN, ADMIN_ID and passwords
docker compose build
docker compose up -d postgres redis   # bring up the databases first
docker compose run --rm bot alembic upgrade head   # apply migrations
docker compose up -d bot      # start the bot
```

Logs: `docker compose logs -f bot`

## Admin commands

Available only to the root administrator (`ADMIN_ID` from the environment).

| Command | Action |
|---------|--------|
| `/users [query]` | paginated user list; `query` searches by part of the name/username |
| `/ban <telegram_id>` | ban (blocked in middleware, never reaches handlers) |
| `/unban <telegram_id>` | unban |
| `/roles` | list roles |
| `/addrole <name> [description]` | add a role to the catalog |
| `/setrole <telegram_id> <name>` | assign a role to a user |

## Migrations

```bash
# After changing models — autogenerate a migration.
# --user keeps the generated file owned by you, not by root; the bind mount
# makes the new file appear on the host (the image has no source mount).
docker compose run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd)/migrations:/app/migrations" \
  bot alembic revision --autogenerate -m "description"

# Apply:
docker compose run --rm bot alembic upgrade head
```

> Alternatively, generate locally from the virtualenv (file is naturally owned
> by you): with Postgres up and `POSTGRES_HOST=localhost` in `.env`, run
> `.venv/bin/alembic revision --autogenerate -m "description"`.
