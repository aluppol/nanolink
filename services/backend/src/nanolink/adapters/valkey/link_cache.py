import logging
from collections.abc import Collection

from redis.asyncio import Redis
from redis.exceptions import RedisError

from nanolink.adapters.valkey.connection import link_cache_key

logger = logging.getLogger(__name__)


class ValkeyLinkCache:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def forget(self, short_codes: Collection[str]) -> None:
        if not short_codes:
            return
        try:
            await self._client.delete(*(link_cache_key(short_code) for short_code in short_codes))
        except RedisError:
            logger.warning("cache invalidation failed; entries expire on their own within 5 minutes")
