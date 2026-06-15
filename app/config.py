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


settings = Settings()