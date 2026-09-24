from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import nats
from nats.aio.client import Client

TASK_STREAM = "LINK_TASKS"
TASK_SUBJECTS = "links.create.*"
CREATOR_CONSUMER = "creator"
RESULT_STREAM = "LINK_RESULTS"
RESULT_SUBJECTS = "links.result.*"
NOTIFIER_CONSUMER = "notifier"
PUBLISH_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class NatsSettings:
    url: str
    user: str
    password: str
    client_name: str


@asynccontextmanager
async def nats_connection(settings: NatsSettings) -> AsyncIterator[Client]:
    client = await nats.connect(
        servers=[settings.url],
        user=settings.user,
        password=settings.password,
        name=settings.client_name,
        max_reconnect_attempts=-1,
        reconnect_time_wait=1,
        connect_timeout=5,
    )
    try:
        yield client
    finally:
        await client.drain()


def task_subject(owner_id: str) -> str:
    return f"links.create.{owner_id}"


def result_subject(owner_id: str) -> str:
    return f"links.result.{owner_id}"
