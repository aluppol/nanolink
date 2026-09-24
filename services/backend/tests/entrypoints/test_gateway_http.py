from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient

from nanolink.application.batch_creation import BatchLinkCreation
from nanolink.application.link_creation import LinkCreationRequests
from nanolink.application.link_management import LinkModeration, OwnedLinkManagement
from nanolink.application.sandbox import DemoSandbox
from nanolink.application.task_reports import TaskReports
from nanolink.domain.links import LinkDraft
from nanolink.domain.sandbox import DEMO_LINK_SEEDS
from nanolink.entrypoints.gateway.app import create_gateway_app
from nanolink.entrypoints.gateway.services import GatewayServices
from nanolink.entrypoints.http_auth import ACCESS_TOKEN_HEADER
from tests.support import (
    ADMIN,
    ALICE,
    BOB,
    GUEST,
    CountingQuota,
    InMemoryLinks,
    InMemoryTaskLedger,
    RecordingCache,
    RecordingQueue,
    RecordingResults,
    ScriptedCodes,
    TokenTable,
    report_mismatches,
)

BASE = "https://nanolink.test"
RESET_TOKEN = "reset-secret"
TOKENS = TokenTable({"alice": ALICE, "bob": BOB, "admin": ADMIN, "guest": GUEST})
ALICE_ID = f"{1:024x}"
BOB_ID = f"{2:024x}"


class Readiness:
    def __init__(self, *, is_ready: bool) -> None:
        self._is_ready = is_ready

    async def is_ready(self) -> bool:
        return self._is_ready


@dataclass
class Fakes:
    links: InMemoryLinks = field(default_factory=InMemoryLinks)
    ledger: InMemoryTaskLedger = field(default_factory=InMemoryTaskLedger)
    queue: RecordingQueue = field(default_factory=RecordingQueue)
    cache: RecordingCache = field(default_factory=RecordingCache)
    quota: CountingQuota = field(default_factory=CountingQuota)


def services_for(fakes: Fakes, readiness: Readiness) -> GatewayServices:
    links = fakes.links
    return GatewayServices(
        verifier=TOKENS,
        creation_requests=LinkCreationRequests(fakes.queue, fakes.ledger, fakes.quota),
        task_reports=TaskReports(fakes.ledger, links),
        owned_links=OwnedLinkManagement(links, links, fakes.cache),
        moderation=LinkModeration(links, links, fakes.cache),
        sandbox=DemoSandbox(links, fakes.ledger, fakes.cache),
        readiness=(readiness,),
        public_base_url=BASE,
        demo_reset_token=RESET_TOKEN,
    )


def client_for(fakes: Fakes, readiness: Readiness | None = None) -> TestClient:
    fakes.links.add_active(LinkDraft("t-alice", "AliceA", "https://example.com/a", ALICE.subject))
    fakes.links.add_active(LinkDraft("t-bob", "BobbyC", "https://example.com/c", BOB.subject))
    services = services_for(fakes, readiness or Readiness(is_ready=True))

    @asynccontextmanager
    async def open_services() -> AsyncIterator[GatewayServices]:
        yield services

    return TestClient(create_gateway_app(open_services))


@dataclass(frozen=True)
class Case:
    id: str
    method: str
    path: str
    token: str | None
    status: int
    body: dict[str, Any] | None = None
    json: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


CASES = [
    Case("no token", "GET", "/api/me", None, 401, {"error": "unauthenticated"}),
    Case("unknown token", "GET", "/api/me", "stolen", 401, {"error": "unauthenticated"}),
    Case(
        "who am I",
        "GET",
        "/api/me",
        "alice",
        200,
        {"username": "alice", "is_admin": False, "daily_quota": 200, "created_today": 0},
    ),
    Case("guest profile", "GET", "/api/me", "guest", 200, {"is_guest": True, "daily_quota": 25}),
    Case(
        "submit a link",
        "POST",
        "/api/links",
        "alice",
        202,
        {"status": "queued"},
        json={"long_url": "https://example.com/new"},
    ),
    Case(
        "submit an internal URL",
        "POST",
        "/api/links",
        "alice",
        422,
        {"error": "invalid_long_url"},
        json={"long_url": "http://keycloak:8080/admin"},
    ),
    Case(
        "submit with an unknown field",
        "POST",
        "/api/links",
        "alice",
        422,
        {"error": "invalid_request"},
        json={"long_url": "https://example.com/", "short_code": "custom"},
    ),
    Case("submit without a body", "POST", "/api/links", "alice", 422, {"error": "invalid_request"}),
    Case("list own links", "GET", "/api/links", "alice", 200, {"next_cursor": None}),
    Case("page size zero", "GET", "/api/links?limit=0", "alice", 422, {"error": "invalid_request"}),
    Case("malformed cursor", "GET", "/api/links?cursor=zz", "alice", 422, {"error": "invalid_request"}),
    Case(
        "read own link",
        "GET",
        f"/api/links/{ALICE_ID}",
        "alice",
        200,
        {"short_code": "AliceA", "short_url": f"{BASE}/AliceA"},
    ),
    Case("read someone else's link", "GET", f"/api/links/{BOB_ID}", "alice", 404, {"error": "not_found"}),
    Case("read a malformed id", "GET", "/api/links/not-an-id", "alice", 404, {"error": "not_found"}),
    Case(
        "change own link",
        "PATCH",
        f"/api/links/{ALICE_ID}",
        "alice",
        200,
        {"long_url": "https://example.com/changed"},
        json={"long_url": "https://example.com/changed"},
    ),
    Case(
        "change to a private address",
        "PATCH",
        f"/api/links/{ALICE_ID}",
        "alice",
        422,
        {"error": "invalid_long_url"},
        json={"long_url": "http://192.168.0.1/"},
    ),
    Case("delete own link", "DELETE", f"/api/links/{ALICE_ID}", "alice", 204),
    Case(
        "delete someone else's link", "DELETE", f"/api/links/{BOB_ID}", "alice", 404, {"error": "not_found"}
    ),
    Case("user lists everything", "GET", "/api/admin/links", "alice", 403, {"error": "forbidden"}),
    Case("admin lists everything", "GET", "/api/admin/links", "admin", 200, {"next_cursor": None}),
    Case("admin moderates", "DELETE", f"/api/admin/links/{BOB_ID}", "admin", 204),
    Case("unknown task", "GET", "/api/tasks/nope", "alice", 404, {"error": "not_found"}),
    Case(
        "demo reset without the token",
        "POST",
        "/internal/demo-reset",
        None,
        401,
        {"error": "unauthenticated"},
    ),
    Case(
        "demo reset with a wrong token",
        "POST",
        "/internal/demo-reset",
        None,
        401,
        {"error": "unauthenticated"},
        headers={"X-Demo-Reset-Token": "guess"},
    ),
    Case(
        "demo reset",
        "POST",
        "/internal/demo-reset",
        None,
        200,
        {"removed": 0, "seeded": len(DEMO_LINK_SEEDS)},
        headers={"X-Demo-Reset-Token": RESET_TOKEN},
    ),
    Case("liveness", "GET", "/healthz", None, 200, {"status": "ok"}),
    Case("readiness", "GET", "/readyz", None, 200, {"status": "ready"}),
    Case("unknown route", "GET", "/api/nothing-here", "alice", 404, {"error": "not_found"}),
]


def run_case(case: Case) -> str | None:
    headers = {**(case.headers or {}), **({ACCESS_TOKEN_HEADER: case.token} if case.token else {})}
    with client_for(Fakes()) as client:
        response = client.request(case.method, case.path, json=case.json, headers=headers)
    body = response.json() if response.content else None
    missing = {key: value for key, value in (case.body or {}).items() if (body or {}).get(key) != value}
    if response.status_code == case.status and not missing:
        return None
    return f"{case.id}: expected {case.status} with {case.body}, got {response.status_code} {body}"


def test_gateway_http_contract() -> None:
    report_mismatches([outcome for case in CASES if (outcome := run_case(case)) is not None])


def test_unauthenticated_answers_name_the_scheme() -> None:
    with client_for(Fakes()) as client:
        response = client.get("/api/me")
    assert response.headers["WWW-Authenticate"] == 'Bearer realm="nanolink"'


def test_readiness_reports_a_missing_dependency() -> None:
    with client_for(Fakes(), Readiness(is_ready=False)) as client:
        response = client.get("/readyz")
    assert (response.status_code, response.json()) == (503, {"status": "not_ready"})


def test_a_submitted_link_can_be_followed_to_its_result() -> None:
    fakes = Fakes()
    with client_for(fakes) as client:
        accepted = client.post(
            "/api/links", json={"long_url": "https://example.com/n"}, headers={ACCESS_TOKEN_HEADER: "bob"}
        )
        task_path = accepted.headers["Location"]
        queued = client.get(task_path, headers={ACCESS_TOKEN_HEADER: "bob"}).json()
        creation = BatchLinkCreation(
            fakes.links, ScriptedCodes(("Fresh1",)), fakes.ledger, RecordingResults()
        )
        client.portal.call(creation.process, fakes.queue.tasks)
        created = client.get(task_path, headers={ACCESS_TOKEN_HEADER: "bob"}).json()
        stranger = client.get(task_path, headers={ACCESS_TOKEN_HEADER: "alice"})
    assert queued["status"] == "queued"
    assert (created["status"], created["link"]["short_url"]) == ("created", f"{BASE}/Fresh1")
    assert stranger.status_code == 404
