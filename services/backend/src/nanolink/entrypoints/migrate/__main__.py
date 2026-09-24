import asyncio

from nanolink.entrypoints.logs import configure_logging
from nanolink.entrypoints.migrate.migration import migrate_with_retries
from nanolink.entrypoints.settings import log_level, migrate_settings


def run() -> None:
    settings = migrate_settings()
    configure_logging(log_level())
    asyncio.run(migrate_with_retries(settings))


if __name__ == "__main__":
    run()
