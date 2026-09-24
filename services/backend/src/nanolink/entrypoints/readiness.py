from collections.abc import Sequence
from typing import Protocol

from nats.aio.client import Client
from pymongo.errors import PyMongoError

from nanolink.adapters.mongo.connection import MongoDatabase


class ReadinessCheck(Protocol):
    async def is_ready(self) -> bool: ...


async def all_ready(checks: Sequence[ReadinessCheck]) -> bool:
    for check in checks:
        if not await check.is_ready():
            return False
    return True


class MongoReadiness:
    def __init__(self, database: MongoDatabase) -> None:
        self._database = database

    async def is_ready(self) -> bool:
        try:
            await self._database.command("ping")
        except PyMongoError:
            return False
        return True


class NatsReadiness:
    def __init__(self, client: Client) -> None:
        self._client = client

    async def is_ready(self) -> bool:
        return bool(self._client.is_connected)
