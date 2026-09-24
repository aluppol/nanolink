from collections.abc import Sequence
from datetime import datetime

from pymongo import UpdateOne

from nanolink.adapters.mongo.connection import TASKS_COLLECTION, MongoDatabase, server_time
from nanolink.adapters.mongo.documents import report_fields, task_record_from_document
from nanolink.domain.tasks import CreateLinkTask, TaskRecord, TaskReport, TaskStatus


class MongoTaskLedger:
    def __init__(self, database: MongoDatabase) -> None:
        self._database = database
        self._tasks = database[TASKS_COLLECTION]

    async def record_queued(self, task: CreateLinkTask) -> None:
        now = await server_time(self._database)
        queued = {
            "owner_id": task.owner_id,
            "status": TaskStatus.QUEUED.value,
            "link_id": None,
            "failure": None,
            "created_at": now,
            "updated_at": now,
        }
        await self._tasks.update_one({"_id": task.task_id}, {"$setOnInsert": queued}, upsert=True)

    async def record_reports(self, reports: Sequence[TaskReport]) -> None:
        if not reports:
            return
        now = await server_time(self._database)
        await self._tasks.bulk_write([_report_upsert(report, now) for report in reports], ordered=False)

    async def find_owned(self, task_id: str, owner_id: str) -> TaskRecord | None:
        document = await self._tasks.find_one({"_id": task_id, "owner_id": owner_id})
        return None if document is None else task_record_from_document(document)

    async def purge_owned(self, owner_id: str) -> None:
        await self._tasks.delete_many({"owner_id": owner_id})


def _report_upsert(report: TaskReport, now: datetime) -> UpdateOne:
    return UpdateOne(
        {"_id": report.task_id},
        {
            "$set": report_fields(report, now),
            "$setOnInsert": {"owner_id": report.owner_id, "created_at": now},
        },
        upsert=True,
    )
