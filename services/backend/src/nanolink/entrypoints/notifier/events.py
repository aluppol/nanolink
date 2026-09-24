import asyncio
from collections.abc import AsyncIterator

from nanolink.domain.tasks import TaskReport
from nanolink.entrypoints.http_views import task_view
from nanolink.entrypoints.notifier.feed import Listener, LiveFeed

RESULT_EVENT = "link-result"
KEEPALIVE_SECONDS = 20.0
STREAM_LIFETIME_SECONDS = 300.0
LISTENER_CAPACITY = 100
RECONNECT_MILLISECONDS = 1000
KEEPALIVE = ": keepalive\n\n"


def new_listener() -> Listener:
    return asyncio.Queue(maxsize=LISTENER_CAPACITY)


async def result_events(
    feed: LiveFeed,
    owner_id: str,
    public_base_url: str,
    listener: Listener,
    lifetime_seconds: float = STREAM_LIFETIME_SECONDS,
) -> AsyncIterator[str]:
    feed.attach(owner_id, listener)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + lifetime_seconds
    try:
        yield f"retry: {RECONNECT_MILLISECONDS}\n\n"
        while (remaining := deadline - loop.time()) > 0:
            yield await _next_event(listener, public_base_url, min(KEEPALIVE_SECONDS, remaining))
    finally:
        feed.detach(owner_id, listener)


async def _next_event(listener: Listener, public_base_url: str, wait_seconds: float) -> str:
    try:
        report = await asyncio.wait_for(listener.get(), wait_seconds)
    except TimeoutError:
        return KEEPALIVE
    return format_result_event(report, public_base_url)


def format_result_event(report: TaskReport, public_base_url: str) -> str:
    data = task_view(report, public_base_url).model_dump_json()
    return f"event: {RESULT_EVENT}\ndata: {data}\n\n"
