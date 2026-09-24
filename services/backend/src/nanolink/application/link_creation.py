from nanolink.domain.errors import DependencyUnavailable, InvalidLongUrl
from nanolink.domain.long_urls import long_url_problem
from nanolink.domain.ports import DailyQuota, TaskLedger, TaskQueue
from nanolink.domain.principals import Principal
from nanolink.domain.tasks import CreateLinkTask


def ensure_valid_long_url(long_url: str) -> None:
    problem = long_url_problem(long_url)
    if problem is not None:
        raise InvalidLongUrl(problem)


class LinkCreationRequests:
    def __init__(self, queue: TaskQueue, ledger: TaskLedger, quota: DailyQuota) -> None:
        self._queue = queue
        self._ledger = ledger
        self._quota = quota

    async def submit(self, principal: Principal, task_id: str, long_url: str) -> None:
        ensure_valid_long_url(long_url)
        await self._consume_quota(principal)
        task = CreateLinkTask(task_id, principal.owner_id, long_url, principal.notify_email)
        await self._enqueue_or_refund(principal, task)
        await self._ledger.record_queued(task)

    async def used_today(self, principal: Principal) -> int:
        return await self._quota.used_today(principal.owner_id)

    async def _consume_quota(self, principal: Principal) -> None:
        if principal.daily_quota is not None:
            await self._quota.consume(principal.owner_id, principal.daily_quota)

    async def _enqueue_or_refund(self, principal: Principal, task: CreateLinkTask) -> None:
        try:
            await self._queue.enqueue(task)
        except DependencyUnavailable:
            if principal.daily_quota is not None:
                await self._quota.refund(principal.owner_id)
            raise
