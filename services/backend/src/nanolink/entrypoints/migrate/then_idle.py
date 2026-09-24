import asyncio
from pathlib import Path

from nanolink.entrypoints.logs import configure_logging
from nanolink.entrypoints.migrate.migration import migrate_with_retries
from nanolink.entrypoints.settings import MigrateSettings, log_level, migrate_settings, required
from nanolink.entrypoints.signals import stop_event


async def migrate_then_idle(settings: MigrateSettings, marker: Path) -> None:
    await migrate_with_retries(settings)
    marker.touch()
    await stop_event().wait()


def run() -> None:
    settings = migrate_settings()
    configure_logging(log_level())
    asyncio.run(migrate_then_idle(settings, Path(required("MIGRATED_FILE"))))


if __name__ == "__main__":
    run()
