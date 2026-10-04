from nanolink.domain.errors import DependencyUnavailable, InvalidLongUrl, QuotaExceeded, SandboxQuotaExceeded
from nanolink.domain.long_urls import long_url_problem
from nanolink.domain.ports import DailyQuota, TaskLedger, TaskQueue
from nanolink.domain.principals import Principal
from nanolink.domain.sandbox import SANDBOX_DAILY_QUOTA, SANDBOX_QUOTA_HOLDER
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
        try:
            await self._queue.enqueue(task)
        except DependencyUnavailable:
            await self._refund_quota(principal)
            raise
        await self._ledger.record_queued(task)

    async def used_today(self, principal: Principal) -> int:
        return await self._quota.used_today(principal.quota_holder)

    async def _consume_quota(self, principal: Principal) -> None:
        if principal.daily_quota is None:
            return
        await self._quota.consume(principal.quota_holder, principal.daily_quota)
        if not principal.is_guest:
            return
        try:
            await self._quota.consume(SANDBOX_QUOTA_HOLDER, SANDBOX_DAILY_QUOTA)
        except QuotaExceeded:
            await self._quota.refund(principal.quota_holder)
            raise SandboxQuotaExceeded from None

    async def _refund_quota(self, principal: Principal) -> None:
        if principal.daily_quota is None:
            return
        await self._quota.refund(principal.quota_holder)
        if principal.is_guest:
            await self._quota.refund(SANDBOX_QUOTA_HOLDER)
