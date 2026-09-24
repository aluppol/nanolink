import asyncio
import json

from nanolink.domain.links import Link
from nanolink.domain.tasks import TaskReport, TaskStatus
from nanolink.entrypoints.notifier.events import (
    KEEPALIVE,
    RECONNECT_MILLISECONDS,
    format_result_event,
    result_events,
)
from nanolink.entrypoints.notifier.feed import LiveFeed
from tests.support import FIXED_TIME

BASE = "https://nanolink.test"
LINK = Link(
    "65f0c1f6e8a3b4c2d9e1f0a1", "aB3xY9", "https://example.com/", "alice-0001", FIXED_TIME, FIXED_TIME
)
ALICE_REPORT = TaskReport("task-1", "alice-0001", TaskStatus.CREATED, LINK, None)
BOB_REPORT = TaskReport("task-2", "bob-0002", TaskStatus.FAILED, None, "boom")


def test_feed_delivers_only_to_the_owner() -> None:
    feed = LiveFeed()
    alice: asyncio.Queue[TaskReport] = asyncio.Queue()
    bob: asyncio.Queue[TaskReport] = asyncio.Queue()
    feed.attach("alice-0001", alice)
    feed.attach("bob-0002", bob)
    feed.publish(ALICE_REPORT)
    assert (alice.qsize(), bob.qsize()) == (1, 0)
    feed.detach("alice-0001", alice)
    feed.publish(ALICE_REPORT)
    assert alice.qsize() == 1
    assert feed.listener_count("alice-0001") == 0


def test_a_full_listener_drops_instead_of_blocking() -> None:
    feed = LiveFeed()
    listener: asyncio.Queue[TaskReport] = asyncio.Queue(maxsize=1)
    feed.attach("alice-0001", listener)
    feed.publish(ALICE_REPORT)
    feed.publish(ALICE_REPORT)
    assert listener.qsize() == 1


def test_events_use_the_public_link_view() -> None:
    event = format_result_event(ALICE_REPORT, BASE)
    name, data = event.removesuffix("\n\n").split("\n")
    assert name == "event: link-result"
    payload = json.loads(data.removeprefix("data: "))
    assert payload["link"]["short_url"] == f"{BASE}/aB3xY9"
    assert payload["status"] == "created"
    assert "notify_email" not in payload


async def test_a_stream_forwards_results_and_detaches_when_it_ends() -> None:
    feed = LiveFeed()
    stream = result_events(feed, "alice-0001", BASE, lifetime_seconds=0.5)
    assert await anext(stream) == f"retry: {RECONNECT_MILLISECONDS}\n\n"
    feed.publish(BOB_REPORT)
    feed.publish(ALICE_REPORT)
    assert "task-1" in await anext(stream)
    remaining = [chunk async for chunk in stream]
    assert remaining == [KEEPALIVE]
    assert feed.listener_count("alice-0001") == 0
