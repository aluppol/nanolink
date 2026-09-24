import asyncio
import logging
from contextlib import AsyncExitStack
from pathlib import Path

from nats.aio.client import Client

from nanolink.adapters.mongo.connection import MongoDatabase, mongo_database
from nanolink.adapters.mongo.links import MongoLinks
from nanolink.adapters.mongo.tasks import MongoTaskLedger
from nanolink.adapters.nats.connection import CREATOR_CONSUMER, TASK_STREAM, nats_connection
from nanolink.adapters.nats.inbox import JetStreamInbox
from nanolink.adapters.nats.publishers import JetStreamResultPublisher
from nanolink.adapters.short_codes import SecretsShortCodeGenerator
from nanolink.application.batch_creation import BatchLinkCreation
from nanolink.entrypoints.creator.worker import PROCESSING_ERRORS, CreatorWorker
from nanolink.entrypoints.logs import configure_logging
from nanolink.entrypoints.settings import CreatorSettings, creator_settings, log_level
from nanolink.entrypoints.signals import stop_event

RETRY_PAUSE_SECONDS = 1.0

logger = logging.getLogger(__name__)


async def assemble_worker(
    settings: CreatorSettings, database: MongoDatabase, nats_client: Client
) -> CreatorWorker:
    jetstream = nats_client.jetstream()
    subscription = await jetstream.pull_subscribe_bind(durable=CREATOR_CONSUMER, stream=TASK_STREAM)
    inbox = JetStreamInbox(subscription, settings.batch_size, settings.batch_wait_seconds)
    links = MongoLinks(database)
    creation = BatchLinkCreation(
        links, SecretsShortCodeGenerator(), MongoTaskLedger(database), JetStreamResultPublisher(jetstream)
    )
    return CreatorWorker(inbox, creation, Path(settings.heartbeat_file))


async def work_until_stopped(worker: CreatorWorker) -> None:
    stop = stop_event()
    while not stop.is_set():
        try:
            await worker.work_once()
        except PROCESSING_ERRORS:
            logger.exception("creator iteration failed; retrying")
            await asyncio.sleep(RETRY_PAUSE_SECONDS)


async def serve(settings: CreatorSettings) -> None:
    async with AsyncExitStack() as stack:
        database = await stack.enter_async_context(mongo_database(settings.mongo))
        nats_client = await stack.enter_async_context(nats_connection(settings.nats))
        await work_until_stopped(await assemble_worker(settings, database, nats_client))


def run() -> None:
    settings = creator_settings()
    configure_logging(log_level())
    asyncio.run(serve(settings))


if __name__ == "__main__":
    run()
