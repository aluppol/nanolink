import asyncio
from pathlib import Path

from nanolink.entrypoints.logs import configure_logging
from nanolink.entrypoints.migrate.migration import migrate_with_retries
from nanolink.entrypoints.settings import log_level, migrate_settings, required
from nanolink.entrypoints.signals import stop_event


async def idle_until_stopped() -> None:
    await stop_event().wait()


def run() -> None:
    settings = migrate_settings()
    configure_logging(log_level())
    asyncio.run(migrate_with_retries(settings))
    Path(required("MIGRATED_FILE")).touch()
    asyncio.run(idle_until_stopped())


if __name__ == "__main__":
    run()
