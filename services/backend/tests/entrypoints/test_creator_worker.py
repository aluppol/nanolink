from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pymongo.errors import ConnectionFailure, OperationFailure

from nanolink.adapters.nats.inbox import MAX_DELIVERIES
from nanolink.adapters.nats.messages import encode_task
from nanolink.domain.tasks import CreateLinkTask
from nanolink.entrypoints.creator.worker import CreatorWorker
from tests.support import report_mismatches


@dataclass
class Metadata:
    num_delivered: int


@dataclass
class Message:
    data: bytes
    metadata: Metadata


def message_for(task_id: str, deliveries: int = 1) -> Message:
    task = CreateLinkTask(task_id, "alice-0001", f"https://example.com/{task_id}", None)
    return Message(encode_task(task), Metadata(deliveries))


@dataclass
class Inbox:
    pending: list[Message]
    acknowledged: list[Message] = field(default_factory=list)
    retried: list[Message] = field(default_factory=list)
    discarded: list[Message] = field(default_factory=list)

    async def next_messages(self) -> list[Message]:
        batch, self.pending = self.pending, []
        return batch

    async def acknowledge(self, messages: Sequence[Message]) -> None:
        self.acknowledged.extend(messages)

    async def retry_later(self, messages: Sequence[Message]) -> None:
        self.retried.extend(messages)

    async def discard(self, messages: Sequence[Message]) -> None:
        self.discarded.extend(messages)


@dataclass
class Creation:
    failing_task_id: str | None
    error: Exception
    abandoned: list[str] = field(default_factory=list)

    async def process(self, tasks: Sequence[CreateLinkTask]) -> None:
        if any(task.task_id == self.failing_task_id for task in tasks):
            raise self.error

    async def abandon(self, tasks: Sequence[CreateLinkTask]) -> None:
        self.abandoned.extend(task.task_id for task in tasks)


def ids(messages: Sequence[Any]) -> list[str]:
    return sorted(message.data.decode().split('"task_id":"')[1].split('"')[0] for message in messages)


GOOD, POISON = message_for("good-1"), message_for("poison")
LAST_TRY_POISON = message_for("poison", MAX_DELIVERIES)
GARBAGE = Message(b"not json", Metadata(1))
REJECTED_WRITE = OperationFailure("Document failed validation", code=121)

CASES = [
    (
        "a clean batch is acknowledged",
        [GOOD, message_for("good-2")],
        None,
        REJECTED_WRITE,
        (["good-1", "good-2"], [], [], []),
    ),
    (
        "one poisoned task does not hold the others back",
        [GOOD, POISON],
        "poison",
        REJECTED_WRITE,
        (["good-1"], ["poison"], [], []),
    ),
    (
        "a poisoned task is abandoned on its last delivery",
        [GOOD, LAST_TRY_POISON],
        "poison",
        REJECTED_WRITE,
        (["good-1"], [], ["poison"], ["poison"]),
    ),
    (
        "an outage retries the whole batch without splitting it",
        [GOOD, POISON],
        "poison",
        ConnectionFailure("mongo is down"),
        ([], ["good-1", "poison"], [], []),
    ),
]


async def run_case(
    messages: list[Message], failing: str | None, error: Exception, tmp: Path
) -> tuple[Any, ...]:
    inbox, creation = Inbox(list(messages)), Creation(failing, error)
    await CreatorWorker(inbox, creation, tmp / "heartbeat").work_once()
    return ids(inbox.acknowledged), ids(inbox.retried), ids(inbox.discarded), sorted(creation.abandoned)


async def test_creator_worker_settles_every_delivery(tmp_path: Path) -> None:
    mismatches = []
    for case_id, messages, failing, error, expected in CASES:
        actual = await run_case(messages, failing, error, tmp_path)
        if actual != expected:
            mismatches.append(f"{case_id}: expected {expected}, got {actual}")
    report_mismatches(mismatches)


async def test_undecodable_messages_are_discarded_and_the_heartbeat_beats(tmp_path: Path) -> None:
    inbox = Inbox([GARBAGE])
    await CreatorWorker(inbox, Creation(None, REJECTED_WRITE), tmp_path / "heartbeat").work_once()
    assert inbox.discarded == [GARBAGE]
    assert (tmp_path / "heartbeat").exists()
