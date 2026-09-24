from nanolink.domain.ports import DailyQuota, LinkCache, SandboxLinks, TaskLedger
from nanolink.domain.sandbox import DEMO_SEED_CODES, SANDBOX_OWNER_ID, seed_drafts


class DemoSandbox:
    def __init__(self, links: SandboxLinks, ledger: TaskLedger, cache: LinkCache, quota: DailyQuota) -> None:
        self._links = links
        self._ledger = ledger
        self._cache = cache
        self._quota = quota

    async def link_count(self) -> int:
        return await self._links.count_owned(SANDBOX_OWNER_ID)

    async def reset(self) -> None:
        stale_codes = await self._links.short_codes_owned(SANDBOX_OWNER_ID)
        await self._links.purge_owned(SANDBOX_OWNER_ID)
        await self._ledger.purge_owned(SANDBOX_OWNER_ID)
        await self._links.insert_drafts(seed_drafts())
        await self._cache.forget(stale_codes | DEMO_SEED_CODES)
        await self._quota.clear(SANDBOX_OWNER_ID)
