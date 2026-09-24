import re
from datetime import datetime

from bson import ObjectId

from nanolink.adapters.mongo.connection import Document
from nanolink.domain.links import Link, LinkDraft
from nanolink.domain.tasks import TaskRecord, TaskReport, TaskStatus

_OBJECT_ID_PATTERN = re.compile(r"[0-9a-f]{24}")


def object_id_or_none(candidate: str) -> ObjectId | None:
    if _OBJECT_ID_PATTERN.fullmatch(candidate) is None:
        return None
    return ObjectId(candidate)


def link_from_document(document: Document) -> Link:
    return Link(
        id=str(document["_id"]),
        short_code=document["short_code"],
        long_url=document["long_url"],
        owner_id=document["owner_id"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def document_from_draft(draft: LinkDraft, now: datetime) -> Document:
    return {
        "short_code": draft.short_code,
        "long_url": draft.long_url,
        "owner_id": draft.owner_id,
        "task_id": draft.task_id,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }


def task_record_from_document(document: Document) -> TaskRecord:
    return TaskRecord(
        task_id=document["_id"],
        owner_id=document["owner_id"],
        status=TaskStatus(document["status"]),
        link_id=document.get("link_id"),
        failure=document.get("failure"),
    )


def report_fields(report: TaskReport, now: datetime) -> Document:
    return {
        "status": report.status.value,
        "link_id": None if report.link is None else report.link.id,
        "failure": report.failure,
        "updated_at": now,
    }
