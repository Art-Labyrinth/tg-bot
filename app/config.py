"""Application configuration.

All settings are read from environment variables (or a local .env file).
pydantic-settings validates them on startup: if BOT_TOKEN is missing we fail
immediately with a clear error, instead of somewhere mid-flow.
"""
from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Telegram ---
    bot_token: SecretStr = SecretStr("")
    # Telegram id of the root administrator (bootstrap superuser, see filters/admin.py).
    admin_id: int = 0

    ticket_service: str = ""

    bot_api_secret: SecretStr = SecretStr("")

    # --- Postgres ---
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "tgbot"
    postgres_user: str = "tgbot"
    postgres_password: str = "tgbot"

    # --- Redis ---
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # --- App ---
    debug: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def postgres_dsn(self) -> str:
        """DSN for the async SQLAlchemy engine (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_dsn(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def missing_required(self) -> list[str]:
        """Names of required settings that are unset (checked at startup).

        An empty BOT_TOKEN makes Telegram answer every call with Unauthorized,
        and a zero ADMIN_ID disables all admin features — both usually mean the
        environment wasn't injected (e.g. compose substituted a blank ${VAR}).
        Failing loudly at boot beats crashing deep inside the first API call.
        """
        missing: list[str] = []
        if not self.bot_token.get_secret_value():
            missing.append("BOT_TOKEN")
        if not self.admin_id:
            missing.append("ADMIN_ID")
        return missing


settings = Settings()