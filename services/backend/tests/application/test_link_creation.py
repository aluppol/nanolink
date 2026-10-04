from collections.abc import Awaitable, Mapping
from dataclasses import dataclass

from nanolink.application.link_creation import LinkCreationRequests
from nanolink.domain.errors import DependencyUnavailable, InvalidLongUrl, QuotaExceeded, SandboxQuotaExceeded
from nanolink.domain.principals import GUEST_DAILY_QUOTA, USER_DAILY_QUOTA, Principal
from nanolink.domain.sandbox import SANDBOX_DAILY_QUOTA, SANDBOX_OWNER_ID
from nanolink.domain.tasks import CreateLinkTask, TaskStatus
from tests.support import (
    ADMIN,
    ALICE,
    GUEST,
    GUEST_IN_OTHER_SESSION,
    GUEST_IN_SESSION,
    CountingQuota,
    InMemoryTaskLedger,
    RecordingQueue,
    UnavailableQueue,
    report_mismatches,
)

URL = "https://example.com/article"
SESSION = "guest-session-1"
OTHER_SESSION = "guest-session-2"
SHARED_GUEST = "guest-guest-0004"
SANDBOX = "sandbox"
Counters = Mapping[str, int]


@dataclass(frozen=True)
class Case:
    id: str
    principal: Principal
    long_url: str
    used_before: Counters
    queue: RecordingQueue | UnavailableQueue
    error: type[Exception] | None
    enqueued: tuple[CreateLinkTask, ...]
    used_after: Counters
    status: TaskStatus | None


def queued_for(owner_id: str, notify_email: str | None) -> tuple[CreateLinkTask, ...]:
    return (CreateLinkTask("task-1", owner_id, URL, notify_email),)


GUEST_QUEUED = queued_for(SANDBOX_OWNER_ID, None)

CASES = [
    Case(
        "user request is queued and counted",
        ALICE,
        URL,
        {},
        RecordingQueue(),
        None,
        queued_for(ALICE.subject, ALICE.email),
        {ALICE.subject: 1},
        TaskStatus.QUEUED,
    ),
    Case(
        "guest request goes to the sandbox and counts for its session and the sandbox",
        GUEST_IN_SESSION,
        URL,
        {},
        RecordingQueue(),
        None,
        GUEST_QUEUED,
        {SESSION: 1, SANDBOX: 1},
        TaskStatus.QUEUED,
    ),
    Case(
        "another session keeps its own quota when one has used theirs up",
        GUEST_IN_OTHER_SESSION,
        URL,
        {SESSION: GUEST_DAILY_QUOTA, SANDBOX: GUEST_DAILY_QUOTA},
        RecordingQueue(),
        None,
        GUEST_QUEUED,
        {SESSION: GUEST_DAILY_QUOTA, OTHER_SESSION: 1, SANDBOX: GUEST_DAILY_QUOTA + 1},
        TaskStatus.QUEUED,
    ),
    Case(
        "guest without a session id is counted by subject",
        GUEST,
        URL,
        {},
        RecordingQueue(),
        None,
        GUEST_QUEUED,
        {SHARED_GUEST: 1, SANDBOX: 1},
        TaskStatus.QUEUED,
    ),
    Case(
        "a session one below its quota is accepted",
        GUEST_IN_SESSION,
        URL,
        {SESSION: GUEST_DAILY_QUOTA - 1, SANDBOX: GUEST_DAILY_QUOTA - 1},
        RecordingQueue(),
        None,
        GUEST_QUEUED,
        {SESSION: GUEST_DAILY_QUOTA, SANDBOX: GUEST_DAILY_QUOTA},
        TaskStatus.QUEUED,
    ),
    Case(
        "a sandbox one below its cap is accepted",
        GUEST_IN_SESSION,
        URL,
        {SANDBOX: SANDBOX_DAILY_QUOTA - 1},
        RecordingQueue(),
        None,
        GUEST_QUEUED,
        {SESSION: 1, SANDBOX: SANDBOX_DAILY_QUOTA},
        TaskStatus.QUEUED,
    ),
    Case(
        "admin has no quota",
        ADMIN,
        URL,
        {},
        RecordingQueue(),
        None,
        queued_for(ADMIN.subject, None),
        {},
        TaskStatus.QUEUED,
    ),
    Case(
        "invalid URL is rejected before the quota",
        ALICE,
        "http://localhost/",
        {},
        RecordingQueue(),
        InvalidLongUrl,
        (),
        {},
        None,
    ),
    Case(
        "user over quota is rejected",
        ALICE,
        URL,
        {ALICE.subject: USER_DAILY_QUOTA},
        RecordingQueue(),
        QuotaExceeded,
        (),
        {ALICE.subject: USER_DAILY_QUOTA},
        None,
    ),
    Case(
        "a session over its quota is rejected and the sandbox count stays unchanged",
        GUEST_IN_SESSION,
        URL,
        {SESSION: GUEST_DAILY_QUOTA, SANDBOX: 30},
        RecordingQueue(),
        QuotaExceeded,
        (),
        {SESSION: GUEST_DAILY_QUOTA, SANDBOX: 30},
        None,
    ),
    Case(
        "a full sandbox rejects a guest and gives the session's count back",
        GUEST_IN_SESSION,
        URL,
        {SANDBOX: SANDBOX_DAILY_QUOTA},
        RecordingQueue(),
        SandboxQuotaExceeded,
        (),
        {SANDBOX: SANDBOX_DAILY_QUOTA},
        None,
    ),
    Case(
        "queue down refunds the quota",
        ALICE,
        URL,
        {ALICE.subject: 3},
        UnavailableQueue(),
        DependencyUnavailable,
        (),
        {ALICE.subject: 3},
        None,
    ),
    Case(
        "queue down refunds the session and the sandbox",
        GUEST_IN_SESSION,
        URL,
        {SESSION: 3, SANDBOX: 9},
        UnavailableQueue(),
        DependencyUnavailable,
        (),
        {SESSION: 3, SANDBOX: 9},
        None,
    ),
]

USED_TODAY_CASES: list[tuple[str, Principal, Counters, int]] = [
    ("a user's own counter", ALICE, {ALICE.subject: 7}, 7),
    ("a guest session's own counter, not the sandbox's", GUEST_IN_SESSION, {SESSION: 4, SANDBOX: 40}, 4),
]


async def error_of(action: Awaitable[None]) -> type[Exception] | None:
    try:
        await action
    except Exception as error:
        return type(error)
    return None


def counted(quota: CountingQuota) -> dict[str, int]:
    return {holder: used for holder, used in quota.used.items() if used}


async def run_case(case: Case) -> str | None:
    queue = RecordingQueue() if isinstance(case.queue, RecordingQueue) else UnavailableQueue()
    ledger = InMemoryTaskLedger()
    quota = CountingQuota(case.used_before)
    requests = LinkCreationRequests(queue, ledger, quota)
    error = await error_of(requests.submit(case.principal, "task-1", case.long_url))
    enqueued = tuple(queue.tasks) if isinstance(queue, RecordingQueue) else ()
    record = ledger.records.get("task-1")
    actual = (error, enqueued, counted(quota), None if record is None else record.status)
    expected = (case.error, case.enqueued, dict(case.used_after), case.status)
    return None if actual == expected else f"{case.id}:\n  expected {expected}\n  got      {actual}"


async def test_link_creation_requests() -> None:
    outcomes = [await run_case(case) for case in CASES]
    report_mismatches([outcome for outcome in outcomes if outcome is not None])


async def test_used_today_reports_the_quota_holders_counter() -> None:
    mismatches = []
    for case_id, principal, counters, expected in USED_TODAY_CASES:
        requests = LinkCreationRequests(RecordingQueue(), InMemoryTaskLedger(), CountingQuota(counters))
        actual = await requests.used_today(principal)
        if actual != expected:
            mismatches.append(f"{case_id}: expected {expected}, got {actual}")
    report_mismatches(mismatches)
