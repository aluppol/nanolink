import logging
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, date, datetime

from redis.asyncio import Redis
from redis.exceptions import RedisError

from nanolink.adapters.valkey.connection import quota_key
from nanolink.domain.errors import QuotaExceeded

KEY_LIFETIME_SECONDS = 2 * 24 * 3600
CONSUME_WITHIN_LIMIT = """
local used = redis.call('INCR', KEYS[1])
if used == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[2])
end
if used > tonumber(ARGV[1]) then
  redis.call('DECR', KEYS[1])
  return 0
end
return 1
"""

logger = logging.getLogger(__name__)


def utc_today() -> date:
    return datetime.now(UTC).date()


class ValkeyDailyQuota:
    def __init__(self, client: Redis, today: Callable[[], date] = utc_today) -> None:
        self._client = client
        self._today = today
        self._consume_within_limit = client.register_script(CONSUME_WITHIN_LIMIT)

    async def consume(self, owner_id: str, limit: int) -> None:
        try:
            allowed = await self._consume_within_limit(
                keys=[self._key(owner_id)], args=[limit, KEY_LIFETIME_SECONDS]
            )
        except RedisError:
            logger.warning("quota store unavailable; allowing the request")
            return
        if not allowed:
            raise QuotaExceeded

    async def refund(self, owner_id: str) -> None:
        with suppress(RedisError):
            await self._client.decr(self._key(owner_id))

    async def clear(self, owner_id: str) -> None:
        with suppress(RedisError):
            await self._client.delete(self._key(owner_id))

    async def used_today(self, owner_id: str) -> int:
        try:
            used = await self._client.get(self._key(owner_id))
        except RedisError:
            return 0
        return int(used or 0)

    def _key(self, owner_id: str) -> str:
        return quota_key(owner_id, self._today())
