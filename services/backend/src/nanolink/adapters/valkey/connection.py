from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(frozen=True, slots=True)
class ValkeySettings:
    host: str
    port: int
    password: str


@asynccontextmanager
async def valkey_client(settings: ValkeySettings) -> AsyncIterator[Redis]:
    client: Redis = Redis(
        host=settings.host,
        port=settings.port,
        password=settings.password,
        decode_responses=True,
        socket_timeout=0.25,
        socket_connect_timeout=0.5,
        health_check_interval=30,
    )
    try:
        yield client
    finally:
        await client.aclose()


def link_cache_key(short_code: str) -> str:
    return f"link:{short_code}"


def quota_key(owner_id: str) -> str:
    return f"quota:{owner_id}"
