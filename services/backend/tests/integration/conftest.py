import os
import uuid
from collections.abc import AsyncIterator

import pytest
from nats.js.client import JetStreamContext
from redis.asyncio import Redis

from nanolink.adapters.mongo.connection import MongoDatabase, MongoSettings, mongo_database
from nanolink.adapters.nats.connection import NatsSettings, nats_connection
from nanolink.adapters.valkey.connection import ValkeySettings, valkey_client


def app_mongo(username: str) -> MongoSettings:
    return MongoSettings(
        host=os.environ["MONGO_HOST"],
        port=27017,
        database=os.environ["MONGO_DATABASE"],
        username=username,
        password=os.environ[f"MONGO_{username.upper()}_PASSWORD"],
        auth_database=os.environ["MONGO_DATABASE"],
        app_name="nanolink-integration-tests",
    )


@pytest.fixture
async def gateway_database() -> AsyncIterator[MongoDatabase]:
    async with mongo_database(app_mongo("gateway")) as database:
        yield database


@pytest.fixture
async def redirect_database() -> AsyncIterator[MongoDatabase]:
    async with mongo_database(app_mongo("redirect")) as database:
        yield database


@pytest.fixture
async def jetstream() -> AsyncIterator[JetStreamContext]:
    settings = NatsSettings(
        url=os.environ["NATS_URL"],
        user=os.environ["NATS_USER"],
        password=os.environ["NATS_PASSWORD"],
        client_name="nanolink-integration-tests",
    )
    async with nats_connection(settings) as client:
        yield client.jetstream()


@pytest.fixture
async def valkey() -> AsyncIterator[Redis]:
    settings = ValkeySettings(
        host=os.environ["VALKEY_HOST"], port=6379, password=os.environ["VALKEY_PASSWORD"]
    )
    async with valkey_client(settings) as client:
        yield client


@pytest.fixture
def owner_id() -> str:
    return f"it-{uuid.uuid4().hex[:12]}"
