import asyncio
from contextlib import suppress

from nanolink.domain.tasks import TaskReport

Listener = asyncio.Queue[TaskReport]


class LiveFeed:
    def __init__(self) -> None:
        self._listeners: dict[str, set[Listener]] = {}

    def attach(self, owner_id: str, listener: Listener) -> None:
        self._listeners.setdefault(owner_id, set()).add(listener)

    def detach(self, owner_id: str, listener: Listener) -> None:
        listeners = self._listeners.get(owner_id, set())
        listeners.discard(listener)
        if not listeners:
            self._listeners.pop(owner_id, None)

    def publish(self, report: TaskReport) -> None:
        for listener in tuple(self._listeners.get(report.owner_id, ())):
            with suppress(asyncio.QueueFull):
                listener.put_nowait(report)

    def listener_count(self, owner_id: str) -> int:
        return len(self._listeners.get(owner_id, ()))
