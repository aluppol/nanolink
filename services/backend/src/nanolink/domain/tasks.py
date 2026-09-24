import uuid
from dataclasses import dataclass
from enum import StrEnum

from nanolink.domain.links import Link

SHORT_CODES_EXHAUSTED = "no free short code was found; please try again"
CREATION_ABANDONED = "the link could not be created; please try again later"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    CREATED = "created"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CreateLinkTask:
    task_id: str
    owner_id: str
    long_url: str
    notify_email: str | None


@dataclass(frozen=True, slots=True)
class TaskRecord:
    task_id: str
    owner_id: str
    status: TaskStatus
    link_id: str | None
    failure: str | None


@dataclass(frozen=True, slots=True)
class TaskReport:
    task_id: str
    owner_id: str
    status: TaskStatus
    link: Link | None
    failure: str | None


@dataclass(frozen=True, slots=True)
class TaskResult:
    report: TaskReport
    notify_email: str | None


def new_task_id() -> str:
    return uuid.uuid4().hex


def created_result(task: CreateLinkTask, link: Link) -> TaskResult:
    report = TaskReport(task.task_id, task.owner_id, TaskStatus.CREATED, link, None)
    return TaskResult(report, task.notify_email)


def failed_result(task: CreateLinkTask, failure: str) -> TaskResult:
    report = TaskReport(task.task_id, task.owner_id, TaskStatus.FAILED, None, failure)
    return TaskResult(report, task.notify_email)
