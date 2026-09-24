from nanolink.application.notifications import CreatorNotifications
from nanolink.application.sandbox import DemoSandbox
from nanolink.application.task_reports import TaskReports
from nanolink.domain.errors import TaskNotFound
from nanolink.domain.links import LinkDraft
from nanolink.domain.sandbox import DEMO_SEED_CODES, SANDBOX_OWNER_ID
from nanolink.domain.tasks import CreateLinkTask, TaskReport, TaskResult, TaskStatus
from tests.support import (
    ALICE,
    BOB,
    GUEST,
    InMemoryLinks,
    InMemoryTaskLedger,
    RecordingCache,
    RecordingEmail,
)

GUEST_ACTIVE = LinkDraft("g-1", "Guest1", "https://example.com/g1", SANDBOX_OWNER_ID)
GUEST_DELETED = LinkDraft("g-2", "Guest2", "https://example.com/g2", SANDBOX_OWNER_ID)
ALICE_LINK = LinkDraft("a-1", "Alice1", "https://example.com/a1", ALICE.subject)


def sandbox_world() -> tuple[InMemoryLinks, InMemoryTaskLedger, RecordingCache, DemoSandbox]:
    links, ledger, cache = InMemoryLinks(), InMemoryTaskLedger(), RecordingCache()
    links.add_active(GUEST_ACTIVE)
    links.add_deleted(GUEST_DELETED)
    links.add_active(ALICE_LINK)
    return links, ledger, cache, DemoSandbox(links, ledger, cache)


async def test_reset_replaces_sandbox_links_with_the_seeds_only() -> None:
    links, ledger, cache, sandbox = sandbox_world()
    await ledger.record_queued(CreateLinkTask("g-9", SANDBOX_OWNER_ID, "https://example.com/g9", None))
    assert await sandbox.link_count() == 2
    await sandbox.reset()
    sandbox_codes = {link.short_code for link in links.active_links() if link.owner_id == SANDBOX_OWNER_ID}
    assert sandbox_codes == set(DEMO_SEED_CODES)
    assert "Alice1" in {link.short_code for link in links.active_links()}
    assert cache.forgotten == {"Guest1", "Guest2"} | set(DEMO_SEED_CODES)
    assert ledger.records == {}


async def test_reset_is_idempotent() -> None:
    links, _, _, sandbox = sandbox_world()
    await sandbox.reset()
    first = sorted((link.short_code, link.long_url) for link in links.active_links())
    await sandbox.reset()
    second = sorted((link.short_code, link.long_url) for link in links.active_links())
    assert first == second


async def test_task_reports_follow_the_ledger_and_ownership() -> None:
    links, ledger = InMemoryLinks(), InMemoryTaskLedger()
    link = links.add_active(LinkDraft("t-1", "Code01", "https://example.com/", ALICE.subject))
    await ledger.record_reports([TaskReport("t-1", ALICE.subject, TaskStatus.CREATED, link, None)])
    await ledger.record_queued(CreateLinkTask("t-2", ALICE.subject, "https://example.com/2", None))
    reports = TaskReports(ledger, links)
    created = await reports.report(ALICE, "t-1")
    queued = await reports.report(ALICE, "t-2")
    assert (created.status, created.link) == (TaskStatus.CREATED, link)
    assert (queued.status, queued.link) == (TaskStatus.QUEUED, None)
    try:
        await reports.report(BOB, "t-1")
    except TaskNotFound:
        return
    raise AssertionError("another owner must not see the task")


async def test_guest_tasks_are_visible_to_every_guest_session() -> None:
    links, ledger = InMemoryLinks(), InMemoryTaskLedger()
    await ledger.record_queued(CreateLinkTask("t-3", SANDBOX_OWNER_ID, "https://example.com/3", None))
    report = await TaskReports(ledger, links).report(GUEST, "t-3")
    assert report.owner_id == SANDBOX_OWNER_ID


async def test_notifications_send_mail_only_with_an_address() -> None:
    email = RecordingEmail()
    notifications = CreatorNotifications(email, "https://nanolink.luppol.com")
    report = TaskReport("t-1", ALICE.subject, TaskStatus.FAILED, None, "boom")
    await notifications.notify(TaskResult(report, None))
    await notifications.notify(TaskResult(report, "alice@example.org"))
    assert [message.recipient for message in email.messages] == ["alice@example.org"]
