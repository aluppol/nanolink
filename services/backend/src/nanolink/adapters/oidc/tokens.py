from collections.abc import Mapping
from typing import Any

import jwt

from nanolink.adapters.oidc.jwks import JwksKeys
from nanolink.domain.errors import NotAuthenticated, NotAuthorized
from nanolink.domain.principals import Principal, Role, is_owner_id

ALLOWED_ALGORITHMS = ["RS256"]
ACCESS_TOKEN_TYPE = "Bearer"
LEEWAY_SECONDS = 30
REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "sub"]
KNOWN_ROLES = frozenset(role.value for role in Role)


class KeycloakTokenVerifier:
    def __init__(self, keys: JwksKeys, issuer: str, audience: str) -> None:
        self._keys = keys
        self._issuer = issuer
        self._audience = audience

    async def verify(self, token: str) -> Principal:
        key = await self._keys.signing_key(_key_id(token))
        if key is None:
            raise NotAuthenticated
        return principal_from_claims(self._claims(token, key))

    def _claims(self, token: str, key: jwt.PyJWK) -> dict[str, Any]:
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                key=key,
                algorithms=ALLOWED_ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWTError as error:
            raise NotAuthenticated from error
        if claims.get("typ") != ACCESS_TOKEN_TYPE:
            raise NotAuthenticated
        return claims


def principal_from_claims(claims: Mapping[str, Any]) -> Principal:
    subject = claims.get("sub")
    roles = _roles(claims)
    if not isinstance(subject, str) or not is_owner_id(subject) or not roles:
        raise NotAuthorized
    username = _text(claims.get("preferred_username")) or subject
    email = _text(claims.get("email")) if claims.get("email_verified") is True else None
    return Principal(subject, username, email, roles)


def _key_id(token: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as error:
        raise NotAuthenticated from error
    key_id = header.get("kid")
    if not isinstance(key_id, str):
        raise NotAuthenticated
    return key_id


def _roles(claims: Mapping[str, Any]) -> frozenset[Role]:
    realm_access = claims.get("realm_access")
    names = realm_access.get("roles") if isinstance(realm_access, Mapping) else None
    if not isinstance(names, list):
        return frozenset()
    return frozenset(Role(name) for name in names if name in KNOWN_ROLES)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
