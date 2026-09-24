from collections.abc import Awaitable
from dataclasses import dataclass

from nanolink.application.link_creation import LinkCreationRequests
from nanolink.domain.errors import DependencyUnavailable, InvalidLongUrl, QuotaExceeded
from nanolink.domain.principals import GUEST_DAILY_QUOTA, USER_DAILY_QUOTA, Principal
from nanolink.domain.sandbox import SANDBOX_OWNER_ID
from nanolink.domain.tasks import CreateLinkTask, TaskStatus
from tests.support import (
    ADMIN,
    ALICE,
    GUEST,
    CountingQuota,
    InMemoryTaskLedger,
    RecordingQueue,
    UnavailableQueue,
    report_mismatches,
)

URL = "https://example.com/article"


@dataclass(frozen=True)
class Case:
    id: str
    principal: Principal
    long_url: str
    used_before: int
    queue: RecordingQueue | UnavailableQueue
    error: type[Exception] | None
    enqueued: tuple[CreateLinkTask, ...]
    used_after: int
    status: TaskStatus | None


def queued_for(owner_id: str, notify_email: str | None) -> tuple[CreateLinkTask, ...]:
    return (CreateLinkTask("task-1", owner_id, URL, notify_email),)


CASES = [
    Case(
        "user request is queued and counted",
        ALICE,
        URL,
        0,
        RecordingQueue(),
        None,
        queued_for(ALICE.subject, ALICE.email),
        1,
        TaskStatus.QUEUED,
    ),
    Case(
        "guest request goes to the sandbox without e-mail",
        GUEST,
        URL,
        0,
        RecordingQueue(),
        None,
        queued_for(SANDBOX_OWNER_ID, None),
        1,
        TaskStatus.QUEUED,
    ),
    Case(
        "admin has no quota",
        ADMIN,
        URL,
        10_000,
        RecordingQueue(),
        None,
        queued_for(ADMIN.subject, None),
        10_000,
        TaskStatus.QUEUED,
    ),
    Case(
        "invalid URL is rejected before the quota",
        ALICE,
        "http://localhost/",
        0,
        RecordingQueue(),
        InvalidLongUrl,
        (),
        0,
        None,
    ),
    Case(
        "user over quota is rejected",
        ALICE,
        URL,
        USER_DAILY_QUOTA,
        RecordingQueue(),
        QuotaExceeded,
        (),
        USER_DAILY_QUOTA,
        None,
    ),
    Case(
        "guest over quota is rejected",
        GUEST,
        URL,
        GUEST_DAILY_QUOTA,
        RecordingQueue(),
        QuotaExceeded,
        (),
        GUEST_DAILY_QUOTA,
        None,
    ),
    Case(
        "queue down refunds the quota", ALICE, URL, 3, UnavailableQueue(), DependencyUnavailable, (), 3, None
    ),
]


async def error_of(action: Awaitable[None]) -> type[Exception] | None:
    try:
        await action
    except Exception as error:
        return type(error)
    return None


async def run_case(case: Case) -> str | None:
    queue = RecordingQueue() if isinstance(case.queue, RecordingQueue) else UnavailableQueue()
    ledger = InMemoryTaskLedger()
    quota = CountingQuota(case.used_before)
    requests = LinkCreationRequests(queue, ledger, quota)
    error = await error_of(requests.submit(case.principal, "task-1", case.long_url))
    enqueued = tuple(queue.tasks) if isinstance(queue, RecordingQueue) else ()
    record = ledger.records.get("task-1")
    actual = (error, enqueued, quota.used, None if record is None else record.status)
    expected = (case.error, case.enqueued, case.used_after, case.status)
    return None if actual == expected else f"{case.id}:\n  expected {expected}\n  got      {actual}"


async def test_link_creation_requests() -> None:
    outcomes = [await run_case(case) for case in CASES]
    report_mismatches([outcome for outcome in outcomes if outcome is not None])


async def test_used_today_reports_the_counter() -> None:
    requests = LinkCreationRequests(RecordingQueue(), InMemoryTaskLedger(), CountingQuota(7))
    assert await requests.used_today(ALICE) == 7
