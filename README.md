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
│   ├── start.py         #   /start — festival announcement (localized)
│   ├── language.py      #   /lang — switch the interface language
│   ├── echo.py          #   echo — future entry point into the AI conversation
│   ├── admin/           #   admin-only handlers (gated by IsAdmin at router level)
│   └── coordinator/     #   /ticket — issue tickets (gated by coordinator role)
├── middlewares/
│   ├── database.py      # opens a DB session for each update
│   └── user.py          # loads/registers the user, checks ban, injects into handlers
├── filters/
│   ├── admin.py         # IsAdmin access filter (root admin from env)
│   └── role.py          # HasRole / HasAnyRole bitmask filters
├── keyboards/
│   ├── admin.py         # admin panel: pagination + role-assign keyboards
│   ├── language.py      # /lang language picker keyboard
│   └── tickets.py       # ticket preview confirm/cancel keyboard
├── i18n/                # lightweight dict-based localization (ru / en / ro)
├── roles.py             # Role bitmask (IntFlag) + names + SQLAlchemy type
├── tickets/             # ticket line parser (pure) + models + prefixes
├── services/
│   ├── redis.py         # Redis client + FSM storage (dialog state)
│   └── tickets.py       # HTTP client for the ticket microservice
└── db/
    ├── base.py          # DeclarativeBase + TimestampMixin
    ├── session.py       # async engine and session factory
    ├── models/          # ORM models (User, UserHistory, IssuedTicket)
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
| `/start` | the festival announcement (localized) |
| `/lang` | pick the interface language (ru / en / ro) |

Localization is a lightweight dict-based catalog in `app/i18n/` (no gettext/.mo
build step). New users get a locale normalized from Telegram's `language_code`
(falling back to `en`); handlers read `user.locale`. Add a language by extending
`Locale`, `LANGUAGE_NAMES` and the message catalog.

## Admin commands

Available only to the root administrator (`ADMIN_ID` from the environment).

| Command | Action |
|---------|--------|
| `/users [query]` | paginated user list (tap a user to assign a role); `query` searches by name/username |
| `/ban <telegram_id>` | ban (blocked in middleware, never reaches handlers) |
| `/unban <telegram_id>` | unban |
| `/roles` | list the available roles |
| `/setrole <telegram_id>` | show role buttons for that user; tapping one assigns it |

Roles are a hardcoded bitmask in `app/roles.py` (`IntFlag`), not a DB table — the
DB stores only the integer on the user. Single roles are powers of two, so a user
can hold several at once and combinations are bitwise OR. Gate handlers with
`HasRole(Role.X)` / `HasAnyRole(...)` from `app/filters/role.py`.

## Coordinator commands

For users with a coordinator role (Masters / Volunteers).

| Command | Action |
|---------|--------|
| `/ticket` | issue tickets from a free-text list (preview + confirm) |

One line per ticket — `[name] [email] [*N]`: a name returns the ticket in chat,
an email sends it (the PNG is also posted), `*N` makes N copies. The ticket
category comes from the coordinator's role; a combo coordinator picks the
category first. Every issued ticket is logged in `issued_tickets`. Generation
calls the ticket microservice (`TICKET_SERVICE`).

## Migrations

Migrations are **applied automatically** on container start (`start.sh` runs
`alembic upgrade head` before launching the bot). You only generate them by hand:

```bash
# After changing models — autogenerate a migration.
# --user keeps the generated file owned by you, not by root. The local stack
# mounts ./migrations writable and ./app read-only, so alembic sees the current
# models and writes the new file straight to your working tree.
docker compose run --rm --user "$(id -u):$(id -g)" \
  bot alembic revision --autogenerate -m "description"

# Apply manually (otherwise it happens on the next container start):
docker compose run --rm bot alembic upgrade head
```

> Custom column types (e.g. the role bitmask, `app/roles.py:RoleType`) are
> rendered in migrations as their DB-level type via `render_item` in
> `migrations/env.py`, so generated files never import application code.
