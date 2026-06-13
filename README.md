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
│   ├── language.py      #   /lang — switch the interface language
│   ├── echo.py          #   echo — future entry point into the AI conversation
│   └── admin/           #   admin-only handlers (gated by IsAdmin at router level)
├── middlewares/
│   ├── database.py      # opens a DB session for each update
│   └── user.py          # loads/registers the user, checks ban, injects into handlers
├── filters/
│   └── admin.py         # IsAdmin access filter
├── keyboards/
│   ├── admin.py         # inline keyboards + callback data for the admin panel
│   └── language.py      # /lang language picker keyboard
├── i18n/                # lightweight dict-based localization (ru / en / ro)
├── services/
│   └── redis.py         # Redis client + FSM storage (dialog state)
└── db/
    ├── base.py          # DeclarativeBase + TimestampMixin
    ├── session.py       # async engine and session factory
    ├── models/          # ORM models (User, UserHistory, Role)
    └── repositories/    # DB queries (repository pattern)
migrations/              # Alembic (async)
deploy/                  # per-environment compose stacks: main (prod), dev (staging)
start.sh                 # container entrypoint: migrate, then run the bot
```

### How it scales

- **New feature** = a new module in `handlers/` with its own `Router`, included in `handlers/__init__.py`. The rest of the code stays untouched.
- **New table** = a model in `db/models/`, re-exported in `db/models/__init__.py`, then autogenerate a migration.
- **DB queries** live in `db/repositories/`, not scattered across handlers.
- **AI layer** later: create `services/ai.py`, call it from `handlers/echo.py`, keep the dialog context in FSM (Redis is already wired up).

## Running (local development)

```bash
cp .env.example .env       # fill in BOT_TOKEN and ADMIN_ID
docker compose up --build -d
```

The bot container runs `start.sh`, which applies migrations (`alembic upgrade
head`) and then starts the bot. Source is mounted **read-only**, so edit on the
host and `docker compose restart bot` to pick changes up.

Logs: `docker compose logs -f bot`

## Deployment

Per-environment stacks live in `deploy/`:

- `deploy/main/docker-compose.yml` — production (`DEBUG=false`)
- `deploy/dev/docker-compose.yml` — staging (`DEBUG=true`)

Each is a full, isolated stack (bot + postgres + redis), namespaced by the
compose project `name:` so dev and main can run on one host without clashing.
Unlike local dev, source is **baked into the image** (no volume) and Postgres is
**not exposed** to the host. The isolated DB uses static, non-secret credentials
defined in the compose file; only the real secrets are injected from the
environment by CI/CD (GitHub Actions).

```bash
# on the server / in CI, with the required env vars exported:
docker compose -f deploy/main/docker-compose.yml up --build -d
```

> Required env vars: `BOT_TOKEN`, `ADMIN_ID` (`DEBUG` is fixed per environment).
> To deploy from a registry instead of building on the server, replace `build:`
> with `image: <your-registry>/tg-bot:<tag>`.

## User commands

| Command | Action |
|---------|--------|
| `/start` | greeting (localized) + a hint to change the language |
| `/lang` | pick the interface language (ru / en / ro) |

Localization is a lightweight dict-based catalog in `app/i18n/` (no gettext/.mo
build step). New users get a locale normalized from Telegram's `language_code`
(falling back to `en`); handlers read `user.locale`. Add a language by extending
`Locale`, `LANGUAGE_NAMES` and the message catalog.

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

Migrations are **applied automatically** on container start (`start.sh` runs
`alembic upgrade head` before launching the bot). You only generate them by hand:

```bash
# After changing models — autogenerate a migration.
# --user keeps the generated file owned by you, not by root; the bind mount
# makes the new file appear on the host (the image has no source mount).
docker compose run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd)/migrations:/app/migrations" \
  bot alembic revision --autogenerate -m "description"

# Apply manually (otherwise it happens on the next container start):
docker compose run --rm bot alembic upgrade head
```

> Alternatively, generate locally from the virtualenv (file is naturally owned
> by you): with Postgres up and `POSTGRES_HOST=localhost` in `.env`, run
> `.venv/bin/alembic revision --autogenerate -m "description"`.
