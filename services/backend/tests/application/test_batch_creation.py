from collections.abc import Sequence
from dataclasses import dataclass, field

from nanolink.application.batch_creation import BatchLinkCreation
from nanolink.domain import long_urls
from nanolink.domain.errors import DependencyUnavailable
from nanolink.domain.links import LinkDraft
from nanolink.domain.tasks import (
    CREATION_ABANDONED,
    INVALID_OWNER,
    SHORT_CODES_EXHAUSTED,
    CreateLinkTask,
    TaskReport,
    TaskStatus,
)
from tests.support import (
    ALICE,
    BOB,
    InMemoryLinks,
    InMemoryTaskLedger,
    RecordingResults,
    ScriptedCodes,
    report_mismatches,
)

URL_A = "https://example.com/a"
TASK_A = CreateLinkTask("task-a", ALICE.subject, URL_A, ALICE.email)
TASK_A_TWIN = CreateLinkTask("task-a-twin", ALICE.subject, URL_A, ALICE.email)
TASK_B = CreateLinkTask("task-b", BOB.subject, URL_A, BOB.email)
TASK_LOCAL = CreateLinkTask("task-local", ALICE.subject, "http://localhost/admin", ALICE.email)
TASK_BAD_OWNER = CreateLinkTask("task-bad-owner", "not.an owner", URL_A, None)

Outcome = tuple[str, str]


@dataclass(frozen=True)
class Case:
    id: str
    tasks: tuple[CreateLinkTask, ...]
    codes: tuple[str, ...]
    expected: dict[str, Outcome]
    active: tuple[LinkDraft, ...] = ()
    deleted: tuple[LinkDraft, ...] = ()
    inserts: int = 1
    results: int = field(default=-1)


CASES = [
    Case("a new task gets the first free code", (TASK_A,), ("Code01",), {"task-a": ("created", "Code01")}),
    Case(
        "a redelivered task keeps its link",
        (TASK_A,),
        (),
        {"task-a": ("created", "Code01")},
        active=(LinkDraft("task-a", "Code01", URL_A, ALICE.subject),),
        inserts=0,
    ),
    Case(
        "the same owner and URL reuse the active link",
        (TASK_A,),
        (),
        {"task-a": ("created", "Old001")},
        active=(LinkDraft("older", "Old001", URL_A, ALICE.subject),),
        inserts=0,
    ),
    Case(
        "a deleted link is not reused",
        (TASK_A,),
        ("Code01",),
        {"task-a": ("created", "Code01")},
        deleted=(LinkDraft("older", "Old001", URL_A, ALICE.subject),),
    ),
    Case(
        "another owner's link is not reused",
        (TASK_B,),
        ("Code02",),
        {"task-b": ("created", "Code02")},
        active=(LinkDraft("older", "Old001", URL_A, ALICE.subject),),
    ),
    Case(
        "two tasks for one URL in a batch share a link",
        (TASK_A, TASK_A_TWIN),
        ("Code01", "Code02"),
        {"task-a": ("created", "Code01"), "task-a-twin": ("created", "Code01")},
    ),
    Case(
        "a taken code is replaced by the next one",
        (TASK_A,),
        ("Taken1", "Code02"),
        {"task-a": ("created", "Code02")},
        active=(LinkDraft("other", "Taken1", URL_A, BOB.subject),),
        inserts=2,
    ),
    Case(
        "codes run out after three attempts",
        (TASK_A,),
        ("Taken1", "Taken1", "Taken1"),
        {"task-a": ("failed", SHORT_CODES_EXHAUSTED)},
        active=(LinkDraft("other", "Taken1", URL_A, BOB.subject),),
        inserts=3,
    ),
    Case(
        "an invalid URL fails without an insert",
        (TASK_LOCAL,),
        (),
        {"task-local": ("failed", long_urls.NOT_A_PUBLIC_DOMAIN)},
        inserts=0,
    ),
    Case(
        "duplicate deliveries in one batch give one result",
        (TASK_A, TASK_A),
        ("Code01",),
        {"task-a": ("created", "Code01")},
        results=1,
    ),
    Case(
        "a malformed owner fails without an insert",
        (TASK_BAD_OWNER,),
        (),
        {"task-bad-owner": ("failed", INVALID_OWNER)},
        inserts=0,
    ),
]


def outcomes_of(results: RecordingResults) -> dict[str, Outcome]:
    return {
        result.report.task_id: (
            result.report.status.value,
            result.report.link.short_code if result.report.link is not None else str(result.report.failure),
        )
        for result in results.results
    }


async def run_case(case: Case) -> str | None:
    links = InMemoryLinks()
    for draft in case.active:
        links.add_active(draft)
    for draft in case.deleted:
        links.add_deleted(draft)
    ledger, results = InMemoryTaskLedger(), RecordingResults()
    await BatchLinkCreation(links, ScriptedCodes(case.codes), ledger, results).process(case.tasks)
    expected_results = len(case.expected) if case.results < 0 else case.results
    actual = (outcomes_of(results), links.insert_calls, len(results.results), set(ledger.records))
    expected = (case.expected, case.inserts, expected_results, set(case.expected))
    return None if actual == expected else f"{case.id}:\n  expected {expected}\n  got      {actual}"


async def test_batch_link_creation() -> None:
    outcomes = [await run_case(case) for case in CASES]
    report_mismatches([outcome for outcome in outcomes if outcome is not None])


async def test_results_carry_the_address_to_notify() -> None:
    results = RecordingResults()
    creation = BatchLinkCreation(InMemoryLinks(), ScriptedCodes(("Code01",)), InMemoryTaskLedger(), results)
    await creation.process([TASK_A])
    assert [result.notify_email for result in results.results] == [ALICE.email]


async def test_abandoned_tasks_are_reported_as_failed() -> None:
    results, ledger = RecordingResults(), InMemoryTaskLedger()
    creation = BatchLinkCreation(InMemoryLinks(), ScriptedCodes(()), ledger, results)
    await creation.abandon([TASK_A, TASK_A, TASK_B])
    assert [(result.report.task_id, result.report.failure) for result in results.results] == [
        ("task-a", CREATION_ABANDONED),
        ("task-b", CREATION_ABANDONED),
    ]
    assert {record.status for record in ledger.records.values()} == {TaskStatus.FAILED}


class UnavailableLedger(InMemoryTaskLedger):
    async def record_reports(self, reports: Sequence[TaskReport]) -> None:
        raise DependencyUnavailable


async def test_abandoning_still_notifies_when_the_ledger_is_down() -> None:
    results = RecordingResults()
    creation = BatchLinkCreation(InMemoryLinks(), ScriptedCodes(()), UnavailableLedger(), results)
    await creation.abandon([TASK_A])
    assert [result.report.task_id for result in results.results] == ["task-a"]
