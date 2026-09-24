from collections.abc import Collection, Mapping, Sequence
from typing import Protocol

from nanolink.domain.links import Link, LinkDraft, LinkPage, PageRequest
from nanolink.domain.notifications import EmailMessage
from nanolink.domain.principals import Principal
from nanolink.domain.tasks import CreateLinkTask, TaskRecord, TaskReport, TaskResult

OwnerUrl = tuple[str, str]


class OwnedLinks(Protocol):
    async def find_owned(self, link_id: str, owner_id: str) -> Link | None: ...

    async def list_owned(self, owner_id: str, page: PageRequest) -> LinkPage: ...


class AllLinks(Protocol):
    async def find_any(self, link_id: str) -> Link | None: ...

    async def list_all(self, page: PageRequest) -> LinkPage: ...


class LinkEditor(Protocol):
    async def change_long_url(self, link_id: str, long_url: str) -> None: ...

    async def soft_delete(self, link_id: str) -> None: ...


class LinkFactory(Protocol):
    async def find_by_task_ids(self, task_ids: Collection[str]) -> Mapping[str, Link]: ...

    async def find_active_by_owner_urls(
        self, owner_urls: Collection[OwnerUrl]
    ) -> Mapping[OwnerUrl, Link]: ...

    async def insert_drafts(self, drafts: Sequence[LinkDraft]) -> None: ...


class SandboxLinks(Protocol):
    async def count_owned(self, owner_id: str) -> int: ...

    async def short_codes_owned(self, owner_id: str) -> frozenset[str]: ...

    async def purge_owned(self, owner_id: str) -> None: ...

    async def insert_drafts(self, drafts: Sequence[LinkDraft]) -> None: ...


class TaskLedger(Protocol):
    async def record_queued(self, task: CreateLinkTask) -> None: ...

    async def record_reports(self, reports: Sequence[TaskReport]) -> None: ...

    async def find_owned(self, task_id: str, owner_id: str) -> TaskRecord | None: ...

    async def purge_owned(self, owner_id: str) -> None: ...


class TaskQueue(Protocol):
    async def enqueue(self, task: CreateLinkTask) -> None: ...


class ResultPublisher(Protocol):
    async def publish(self, results: Sequence[TaskResult]) -> None: ...


class LinkCache(Protocol):
    async def forget(self, short_codes: Collection[str]) -> None: ...


class DailyQuota(Protocol):
    async def consume(self, owner_id: str, limit: int) -> None: ...

    async def refund(self, owner_id: str) -> None: ...

    async def used_today(self, owner_id: str) -> int: ...

    async def clear(self, owner_id: str) -> None: ...


class ShortCodeGenerator(Protocol):
    def next_code(self) -> str: ...


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> Principal: ...


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...
