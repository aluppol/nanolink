from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

Document = dict[str, Any]
MongoDatabase = AsyncDatabase[Document]
MongoClient = AsyncMongoClient[Document]

LINKS_COLLECTION = "links"
TASKS_COLLECTION = "tasks"
DUPLICATE_KEY_ERROR = 11000


@dataclass(frozen=True, slots=True)
class MongoSettings:
    host: str
    port: int
    database: str
    username: str
    password: str
    auth_database: str
    app_name: str


@asynccontextmanager
async def mongo_client(settings: MongoSettings) -> AsyncIterator[MongoClient]:
    client: MongoClient = AsyncMongoClient(
        host=settings.host,
        port=settings.port,
        username=settings.username,
        password=settings.password,
        authSource=settings.auth_database,
        appname=settings.app_name,
        tz_aware=True,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    try:
        yield client
    finally:
        await client.close()


@asynccontextmanager
async def mongo_database(settings: MongoSettings) -> AsyncIterator[MongoDatabase]:
    async with mongo_client(settings) as client:
        yield client[settings.database]


async def server_time(database: MongoDatabase) -> datetime:
    reply = await database.command("hello")
    local_time: datetime = reply["localTime"]
    return local_time
