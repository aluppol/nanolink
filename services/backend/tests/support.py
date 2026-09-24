import itertools
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from nanolink.domain.errors import DependencyUnavailable, DuplicateLongUrl, NotAuthenticated, QuotaExceeded
from nanolink.domain.links import Link, LinkDraft, LinkPage, PageRequest
from nanolink.domain.notifications import EmailMessage
from nanolink.domain.ports import OwnerUrl
from nanolink.domain.principals import Principal, Role
from nanolink.domain.tasks import CreateLinkTask, TaskRecord, TaskReport, TaskResult, TaskStatus

FIXED_TIME = datetime(2026, 9, 24, 3, 0, tzinfo=UTC)

ALICE = Principal("alice-0001", "alice", "alice@example.org", frozenset({Role.USER}))
BOB = Principal("bob-0002", "bob", "bob@example.org", frozenset({Role.USER}))
ADMIN = Principal("admin-0003", "admin", None, frozenset({Role.ADMIN}))
GUEST = Principal("guest-0004", "guest", "recruiter@example.org", frozenset({Role.GUEST}))


def report_mismatches(mismatches: Sequence[str]) -> None:
    assert not mismatches, "\n" + "\n".join(mismatches)


@dataclass
class StoredLink:
    link: Link
    task_id: str
    is_deleted: bool


class InMemoryLinks:
    def __init__(self) -> None:
        self.rows: list[StoredLink] = []
        self.insert_calls = 0
        self._ids: Iterator[int] = itertools.count(1)

    def add_active(self, draft: LinkDraft) -> Link:
        link = self._link_for(draft)
        self.rows.append(StoredLink(link, draft.task_id, is_deleted=False))
        return link

    def add_deleted(self, draft: LinkDraft) -> Link:
        link = self._link_for(draft)
        self.rows.append(StoredLink(link, draft.task_id, is_deleted=True))
        return link

    def active_links(self) -> list[Link]:
        return [row.link for row in self.rows if not row.is_deleted]

    async def find_owned(self, link_id: str, owner_id: str) -> Link | None:
        return next(
            (link for link in self.active_links() if (link.id, link.owner_id) == (link_id, owner_id)), None
        )

    async def find_any(self, link_id: str) -> Link | None:
        return next((link for link in self.active_links() if link.id == link_id), None)

    async def list_owned(self, owner_id: str, page: PageRequest) -> LinkPage:
        return _page([link for link in self.active_links() if link.owner_id == owner_id], page)

    async def list_all(self, page: PageRequest) -> LinkPage:
        return _page(self.active_links(), page)

    async def change_long_url(self, link_id: str, long_url: str) -> None:
        row = self._active_row(link_id)
        if row is None:
            return
        if any(
            link.id != link_id and (link.owner_id, link.long_url) == (row.link.owner_id, long_url)
            for link in self.active_links()
        ):
            raise DuplicateLongUrl
        row.link = replace(row.link, long_url=long_url)

    async def soft_delete(self, link_id: str) -> None:
        row = self._active_row(link_id)
        if row is not None:
            row.is_deleted = True

    async def find_by_task_ids(self, task_ids: Collection[str]) -> Mapping[str, Link]:
        return {row.task_id: row.link for row in self.rows if row.task_id in task_ids}

    async def find_active_by_owner_urls(self, owner_urls: Collection[OwnerUrl]) -> Mapping[OwnerUrl, Link]:
        return {
            (link.owner_id, link.long_url): link
            for link in self.active_links()
            if (link.owner_id, link.long_url) in owner_urls
        }

    async def insert_drafts(self, drafts: Sequence[LinkDraft]) -> None:
        self.insert_calls += 1
        for draft in drafts:
            if not self._violates_uniqueness(draft):
                self.add_active(draft)

    async def count_owned(self, owner_id: str) -> int:
        return sum(1 for row in self.rows if row.link.owner_id == owner_id)

    async def short_codes_owned(self, owner_id: str) -> frozenset[str]:
        return frozenset(row.link.short_code for row in self.rows if row.link.owner_id == owner_id)

    async def purge_owned(self, owner_id: str) -> None:
        self.rows = [row for row in self.rows if row.link.owner_id != owner_id]

    def _active_row(self, link_id: str) -> StoredLink | None:
        return next((row for row in self.rows if row.link.id == link_id and not row.is_deleted), None)

    def _violates_uniqueness(self, draft: LinkDraft) -> bool:
        return any(
            row.link.short_code == draft.short_code
            or row.task_id == draft.task_id
            or (
                not row.is_deleted
                and (row.link.owner_id, row.link.long_url) == (draft.owner_id, draft.long_url)
            )
            for row in self.rows
        )

    def _link_for(self, draft: LinkDraft) -> Link:
        link_id = f"{next(self._ids):024x}"
        return Link(link_id, draft.short_code, draft.long_url, draft.owner_id, FIXED_TIME, FIXED_TIME)


def _page(links: list[Link], page: PageRequest) -> LinkPage:
    newest_first = sorted(links, key=lambda link: link.id, reverse=True)
    after_cursor = [link for link in newest_first if page.cursor is None or link.id < page.cursor]
    selected = tuple(after_cursor[: page.limit])
    has_more = len(after_cursor) > page.limit
    return LinkPage(selected, selected[-1].id if has_more else None)


class InMemoryTaskLedger:
    def __init__(self) -> None:
        self.records: dict[str, TaskRecord] = {}

    async def record_queued(self, task: CreateLinkTask) -> None:
        self.records.setdefault(
            task.task_id, TaskRecord(task.task_id, task.owner_id, TaskStatus.QUEUED, None, None)
        )

    async def record_reports(self, reports: Sequence[TaskReport]) -> None:
        for report in reports:
            link_id = None if report.link is None else report.link.id
            self.records[report.task_id] = TaskRecord(
                report.task_id, report.owner_id, report.status, link_id, report.failure
            )

    async def find_owned(self, task_id: str, owner_id: str) -> TaskRecord | None:
        record = self.records.get(task_id)
        return record if record is not None and record.owner_id == owner_id else None

    async def purge_owned(self, owner_id: str) -> None:
        self.records = {key: record for key, record in self.records.items() if record.owner_id != owner_id}


class RecordingQueue:
    def __init__(self) -> None:
        self.tasks: list[CreateLinkTask] = []

    async def enqueue(self, task: CreateLinkTask) -> None:
        self.tasks.append(task)


class UnavailableQueue:
    async def enqueue(self, task: CreateLinkTask) -> None:
        raise DependencyUnavailable


class RecordingResults:
    def __init__(self) -> None:
        self.results: list[TaskResult] = []

    async def publish(self, results: Sequence[TaskResult]) -> None:
        self.results.extend(results)


class RecordingCache:
    def __init__(self) -> None:
        self.forgotten: set[str] = set()

    async def forget(self, short_codes: Collection[str]) -> None:
        self.forgotten.update(short_codes)


class CountingQuota:
    def __init__(self, used: int = 0) -> None:
        self.used = used

    async def consume(self, owner_id: str, limit: int) -> None:
        self.used += 1
        if self.used > limit:
            self.used -= 1
            raise QuotaExceeded

    async def refund(self, owner_id: str) -> None:
        self.used -= 1

    async def used_today(self, owner_id: str) -> int:
        return self.used

    async def clear(self, owner_id: str) -> None:
        self.used = 0


class ScriptedCodes:
    def __init__(self, codes: Sequence[str]) -> None:
        self._codes = iter(codes)

    def next_code(self) -> str:
        return next(self._codes)


class RecordingEmail:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


class TokenTable:
    def __init__(self, principals: Mapping[str, Principal]) -> None:
        self._principals = principals

    async def verify(self, token: str) -> Principal:
        principal = self._principals.get(token)
        if principal is None:
            raise NotAuthenticated
        return principal
