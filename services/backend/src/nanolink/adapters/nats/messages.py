from datetime import datetime

from pydantic import BaseModel, ConfigDict, ValidationError

from nanolink.domain.links import Link
from nanolink.domain.tasks import CreateLinkTask, TaskReport, TaskResult, TaskStatus


class _Message(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")


class TaskMessage(_Message):
    task_id: str
    owner_id: str
    long_url: str
    notify_email: str | None


class LinkMessage(_Message):
    id: str
    short_code: str
    long_url: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class ResultMessage(_Message):
    task_id: str
    owner_id: str
    status: TaskStatus
    link: LinkMessage | None
    failure: str | None
    notify_email: str | None


def encode_task(task: CreateLinkTask) -> bytes:
    message = TaskMessage(
        task_id=task.task_id, owner_id=task.owner_id, long_url=task.long_url, notify_email=task.notify_email
    )
    return message.model_dump_json().encode()


def decode_task(payload: bytes) -> CreateLinkTask | None:
    try:
        message = TaskMessage.model_validate_json(payload)
    except ValidationError:
        return None
    return CreateLinkTask(message.task_id, message.owner_id, message.long_url, message.notify_email)


def encode_result(result: TaskResult) -> bytes:
    report = result.report
    link = None if report.link is None else link_message(report.link)
    message = ResultMessage(
        task_id=report.task_id,
        owner_id=report.owner_id,
        status=report.status,
        link=link,
        failure=report.failure,
        notify_email=result.notify_email,
    )
    return message.model_dump_json().encode()


def decode_result(payload: bytes) -> TaskResult | None:
    try:
        message = ResultMessage.model_validate_json(payload)
    except ValidationError:
        return None
    link = None if message.link is None else Link(**message.link.model_dump())
    report = TaskReport(message.task_id, message.owner_id, message.status, link, message.failure)
    return TaskResult(report, message.notify_email)


def link_message(link: Link) -> LinkMessage:
    return LinkMessage(
        id=link.id,
        short_code=link.short_code,
        long_url=link.long_url,
        owner_id=link.owner_id,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )
