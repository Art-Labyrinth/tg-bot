"""Redis: FSM storage for aiogram + a reusable client.

FSM storage is needed to remember the dialog state between a user's messages —
the foundation for future neural-network conversations (context, scenario
steps, etc.). Redis survives bot restarts and is shared across replicas.
"""
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.config import settings


def create_redis() -> Redis:
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )


def create_storage(redis: Redis) -> RedisStorage:
    return RedisStorage(redis=redis)
