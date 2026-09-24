import asyncio
import logging

from nats.errors import Error as NatsError
from pymongo.errors import PyMongoError

from nanolink.adapters.mongo.connection import mongo_client
from nanolink.adapters.mongo.schema import DatabaseUser, migrate_database
from nanolink.adapters.nats.connection import nats_connection
from nanolink.adapters.nats.streams import migrate_streams
from nanolink.entrypoints.settings import MigrateSettings

APP_USERS = (("gateway", "readWrite"), ("creator", "readWrite"), ("redirect", "read"))
ATTEMPTS = 30
PAUSE_SECONDS = 2.0

logger = logging.getLogger(__name__)


async def migrate(settings: MigrateSettings) -> None:
    users = [DatabaseUser(name, settings.user_passwords[name], role) for name, role in APP_USERS]
    async with mongo_client(settings.root_mongo) as client:
        await migrate_database(client[settings.root_mongo.database], users)
    async with nats_connection(settings.nats) as nats_client:
        await migrate_streams(nats_client.jetstream())


async def migrate_with_retries(settings: MigrateSettings) -> None:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            await migrate(settings)
        except (PyMongoError, NatsError, OSError) as error:
            logger.warning("migration attempt %d/%d failed: %r", attempt, ATTEMPTS, error)
            await asyncio.sleep(PAUSE_SECONDS)
            continue
        logger.info("database and streams are up to date")
        return
    raise SystemExit("migrations failed")

