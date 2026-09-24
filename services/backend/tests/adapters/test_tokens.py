import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from nanolink.adapters.oidc.jwks import JwksKeys
from nanolink.adapters.oidc.tokens import KeycloakTokenVerifier
from nanolink.domain.errors import DependencyUnavailable, NotAuthenticated, NotAuthorized
from nanolink.domain.principals import Principal, Role
from nanolink.domain.sandbox import SANDBOX_OWNER_ID
from tests.support import report_mismatches

ISSUER = "https://auth.example.test/realms/luppol"
AUDIENCE = "nanolink"
JWKS_URL = "https://auth.example.test/realms/luppol/protocol/openid-connect/certs"
KEY_ID = "key-1"
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
FOREIGN_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks_document() -> dict[str, Any]:
    public_jwk = json.loads(RSAAlgorithm.to_jwk(SIGNING_KEY.public_key()))
    return {"keys": [{**public_jwk, "kid": KEY_ID, "use": "sig", "alg": "RS256"}]}


def claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    base = {
        "iss": ISSUER,
        "aud": [AUDIENCE, "account"],
        "sub": "alice-0001",
        "typ": "Bearer",
        "iat": now,
        "exp": now + 300,
        "preferred_username": "alice",
        "email": "alice@example.org",
        "email_verified": True,
        "realm_access": {"roles": ["USER", "default-roles-luppol"]},
    }
    return {key: value for key, value in {**base, **overrides}.items() if value is not None}


def signed(payload: dict[str, Any], key: rsa.RSAPrivateKey = SIGNING_KEY, key_id: str = KEY_ID) -> str:
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": key_id})


def base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def confused_hs256_token() -> str:
    public_pem = SIGNING_KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    header = base64url(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KEY_ID}).encode())
    payload = base64url(json.dumps(claims()).encode())
    signature = hmac.new(public_pem, f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{base64url(signature)}"


def unsigned_token() -> str:
    return jwt.encode(claims(), None, algorithm="none", headers={"kid": KEY_ID})


@dataclass
class JwksServer:
    status: int = 200
    keys_served: bool = True
    requests: list[str] = field(default_factory=list)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        document = jwks_document() if self.keys_served else {"keys": [unrelated_key()]}
        return httpx.Response(self.status, json=document)


def unrelated_key() -> dict[str, Any]:
    public_jwk = json.loads(RSAAlgorithm.to_jwk(FOREIGN_KEY.public_key()))
    return {**public_jwk, "kid": "key-rotated", "use": "sig", "alg": "RS256"}


def verifier_for(server: JwksServer, clock: list[float] | None = None) -> KeycloakTokenVerifier:
    http = httpx.AsyncClient(transport=httpx.MockTransport(server.handle))
    ticks = clock if clock is not None else [0.0]
    return KeycloakTokenVerifier(JwksKeys(http, JWKS_URL, clock=lambda: ticks[0]), ISSUER, AUDIENCE)


ALICE = Principal("alice-0001", "alice", "alice@example.org", frozenset({Role.USER}))
Expected = Principal | type[Exception]

CASES: list[tuple[str, str, Expected]] = [
    ("a valid access token", signed(claims()), ALICE),
    ("an expired token", signed(claims(exp=int(time.time()) - 120)), NotAuthenticated),
    ("another issuer", signed(claims(iss="https://evil.example/realms/luppol")), NotAuthenticated),
    ("another audience", signed(claims(aud="life-balance")), NotAuthenticated),
    ("an ID token", signed(claims(typ="ID")), NotAuthenticated),
    ("no subject", signed(claims(sub=None)), NotAuthenticated),
    ("a foreign signature", signed(claims(), key=FOREIGN_KEY), NotAuthenticated),
    ("an unknown key id", signed(claims(), key_id="key-2"), NotAuthenticated),
    ("HS256 signed with the public key", confused_hs256_token(), NotAuthenticated),
    ("an unsigned token", unsigned_token(), NotAuthenticated),
    ("not a token at all", "not-a-jwt", NotAuthenticated),
    ("no NanoLink role", signed(claims(realm_access={"roles": ["default-roles-luppol"]})), NotAuthorized),
    ("a subject that cannot be an owner id", signed(claims(sub="a.b")), NotAuthorized),
    (
        "an unverified e-mail is not used",
        signed(claims(email_verified=False)),
        Principal("alice-0001", "alice", None, frozenset({Role.USER})),
    ),
    (
        "a guest",
        signed(claims(realm_access={"roles": ["guest"]})),
        Principal("alice-0001", "alice", "alice@example.org", frozenset({Role.GUEST})),
    ),
]


async def outcome_of(verifier: KeycloakTokenVerifier, token: str) -> Expected:
    try:
        return await verifier.verify(token)
    except Exception as error:
        return type(error)


async def test_token_verification_rules() -> None:
    verifier = verifier_for(JwksServer())
    mismatches = [
        f"{case_id}: expected {expected}, got {actual}"
        for case_id, token, expected in CASES
        if (actual := await outcome_of(verifier, token)) != expected
    ]
    report_mismatches(mismatches)


async def test_guest_principal_works_in_the_sandbox() -> None:
    principal = await verifier_for(JwksServer()).verify(signed(claims(realm_access={"roles": ["guest"]})))
    assert principal.owner_id == SANDBOX_OWNER_ID


async def test_keys_are_fetched_once_and_refreshed_at_most_every_thirty_seconds() -> None:
    server, clock = JwksServer(), [0.0]
    verifier = verifier_for(server, clock)
    await verifier.verify(signed(claims()))
    await verifier.verify(signed(claims()))
    await outcome_of(verifier, signed(claims(), key_id="key-2"))
    clock[0] = 31.0
    await outcome_of(verifier, signed(claims(), key_id="key-2"))
    assert len(server.requests) == 2


async def test_a_key_removed_from_the_endpoint_stops_working_within_ten_minutes() -> None:
    server, clock = JwksServer(), [0.0]
    verifier = verifier_for(server, clock)
    assert await outcome_of(verifier, signed(claims())) == ALICE
    server.keys_served = False
    clock[0] = 601.0
    assert await outcome_of(verifier, signed(claims())) == NotAuthenticated
    assert len(server.requests) == 2


async def test_an_unreachable_key_endpoint_is_reported_and_retried_after_a_pause() -> None:
    server, clock = JwksServer(status=503), [0.0]
    verifier = verifier_for(server, clock)
    first = await outcome_of(verifier, signed(claims()))
    during_pause = await outcome_of(verifier, signed(claims()))
    server.status, clock[0] = 200, 6.0
    after_pause = await outcome_of(verifier, signed(claims()))
    assert (first, during_pause, after_pause) == (DependencyUnavailable, DependencyUnavailable, ALICE)
    assert len(server.requests) == 2
