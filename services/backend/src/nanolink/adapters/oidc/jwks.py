import time
from collections.abc import Callable

import httpx
import jwt

from nanolink.domain.errors import DependencyUnavailable

UNKNOWN_KEY_REFRESH_SECONDS = 30.0
KEY_SET_MAX_AGE_SECONDS = 600.0
FAILURE_BACKOFF_SECONDS = 5.0
FETCH_TIMEOUT_SECONDS = 5.0


class JwksKeys:
    def __init__(
        self,
        http: httpx.AsyncClient,
        jwks_url: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._http = http
        self._jwks_url = jwks_url
        self._clock = clock
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at: float | None = None
        self._failed_at: float | None = None

    async def signing_key(self, key_id: str) -> jwt.PyJWK | None:
        if self._is_refresh_due(key_id):
            await self._refresh()
        return self._keys.get(key_id)

    def _is_refresh_due(self, key_id: str) -> bool:
        now = self._clock()
        if self._failed_at is not None and now - self._failed_at < FAILURE_BACKOFF_SECONDS:
            raise DependencyUnavailable
        if self._fetched_at is None:
            return True
        age = now - self._fetched_at
        is_unknown = key_id not in self._keys
        return age >= KEY_SET_MAX_AGE_SECONDS or (is_unknown and age >= UNKNOWN_KEY_REFRESH_SECONDS)

    async def _refresh(self) -> None:
        try:
            response = await self._http.get(self._jwks_url, timeout=FETCH_TIMEOUT_SECONDS)
            response.raise_for_status()
            key_set = jwt.PyJWKSet.from_dict(response.json())
        except (httpx.HTTPError, jwt.PyJWTError, ValueError) as error:
            self._failed_at = self._clock()
            raise DependencyUnavailable from error
        self._keys = {key.key_id: key for key in key_set.keys if key.key_id and key.public_key_use != "enc"}
        self._fetched_at = self._clock()
        self._failed_at = None
