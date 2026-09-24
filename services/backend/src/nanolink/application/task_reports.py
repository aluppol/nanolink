from nanolink.domain.errors import TaskNotFound
from nanolink.domain.links import Link
from nanolink.domain.ports import OwnedLinks, TaskLedger
from nanolink.domain.principals import Principal
from nanolink.domain.tasks import TaskRecord, TaskReport


class TaskReports:
    def __init__(self, ledger: TaskLedger, links: OwnedLinks) -> None:
        self._ledger = ledger
        self._links = links

    async def report(self, principal: Principal, task_id: str) -> TaskReport:
        record = await self._ledger.find_owned(task_id, principal.owner_id)
        if record is None:
            raise TaskNotFound
        link = await self._link_of(record)
        return TaskReport(record.task_id, record.owner_id, record.status, link, record.failure)

    async def _link_of(self, record: TaskRecord) -> Link | None:
        if record.link_id is None:
            return None
        return await self._links.find_owned(record.link_id, record.owner_id)
