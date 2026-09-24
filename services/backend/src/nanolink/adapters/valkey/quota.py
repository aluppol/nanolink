import logging
from contextlib import suppress

from redis.asyncio import Redis
from redis.exceptions import RedisError

from nanolink.adapters.valkey.connection import quota_key
from nanolink.domain.errors import QuotaExceeded

WINDOW_SECONDS = 24 * 3600

logger = logging.getLogger(__name__)


class ValkeyDailyQuota:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def consume(self, owner_id: str, limit: int) -> None:
        used = await self._increment(owner_id)
        if used is not None and used > limit:
            await self.refund(owner_id)
            raise QuotaExceeded

    async def refund(self, owner_id: str) -> None:
        with suppress(RedisError):
            await self._client.decr(quota_key(owner_id))

    async def clear(self, owner_id: str) -> None:
        with suppress(RedisError):
            await self._client.delete(quota_key(owner_id))

    async def used_today(self, owner_id: str) -> int:
        try:
            used = await self._client.get(quota_key(owner_id))
        except RedisError:
            return 0
        return int(used or 0)

    async def _increment(self, owner_id: str) -> int | None:
        key = quota_key(owner_id)
        try:
            async with self._client.pipeline(transaction=True) as pipeline:
                pipeline.set(key, 0, ex=WINDOW_SECONDS, nx=True)
                pipeline.incr(key)
                replies = await pipeline.execute()
        except RedisError:
            logger.warning("quota store unavailable; allowing the request")
            return None
        return int(replies[1])
