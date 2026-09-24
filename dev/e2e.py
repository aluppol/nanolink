import asyncio
import json
import sys
import uuid

import httpx

BASE_URL = "http://devauth:8090"
RESULT_TIMEOUT_SECONDS = 20.0


async def signed_in(username: str) -> httpx.AsyncClient:
    client = httpx.AsyncClient(base_url=BASE_URL, follow_redirects=False, timeout=10)
    await client.get(f"/__dev/login/{username}")
    return client


async def polled_result(client: httpx.AsyncClient, task_id: str) -> dict[str, object]:
    for _ in range(int(RESULT_TIMEOUT_SECONDS * 4)):
        report = (await client.get(f"/api/tasks/{task_id}")).json()
        if report["status"] != "queued":
            return dict(report)
        await asyncio.sleep(0.25)
    raise AssertionError(f"task {task_id} stayed queued")


async def created_via_stream_and_task(alice: httpx.AsyncClient, long_url: str) -> dict[str, object]:
    listening = asyncio.Event()
    stream = asyncio.create_task(listen_for_any_result(alice, listening))
    await asyncio.wait_for(listening.wait(), RESULT_TIMEOUT_SECONDS)
    accepted = await alice.post("/api/links", json={"long_url": long_url})
    assert accepted.status_code == 202, accepted.text
    task_id = accepted.json()["task_id"]
    streamed = await asyncio.wait_for(stream, RESULT_TIMEOUT_SECONDS)
    assert streamed["task_id"] == task_id, streamed
    polled = await polled_result(alice, task_id)
    assert polled["status"] == "created", polled
    return polled


async def listen_for_any_result(client: httpx.AsyncClient, listening: asyncio.Event) -> dict[str, object]:
    async with client.stream("GET", "/api/notifications", timeout=None) as stream:
        async for line in stream.aiter_lines():
            if line.startswith("retry:"):
                listening.set()
            if line.startswith("data: "):
                return dict(json.loads(line.removeprefix("data: ")))
    raise AssertionError("the notification stream ended early")


async def redirect_target(client: httpx.AsyncClient, short_code: str) -> tuple[int, str | None]:
    response = await client.get(f"/{short_code}")
    return response.status_code, response.headers.get("location")


async def owner_lifecycle() -> str:
    alice = await signed_in("alice")
    long_url = f"https://example.com/e2e/{uuid.uuid4().hex}"
    report = await created_via_stream_and_task(alice, long_url)
    link = report["link"]
    assert isinstance(link, dict)
    code, link_id = link["short_code"], link["id"]
    assert await redirect_target(alice, code) == (302, long_url)
    again = await polled_result(
        alice, (await alice.post("/api/links", json={"long_url": long_url})).json()["task_id"]
    )
    assert again["link"]["short_code"] == code, again
    changed = await alice.patch(f"/api/links/{link_id}", json={"long_url": f"{long_url}/changed"})
    assert changed.status_code == 200, changed.text
    assert await redirect_target(alice, code) == (302, f"{long_url}/changed")
    assert (await alice.delete(f"/api/links/{link_id}")).status_code == 204
    assert (await redirect_target(alice, code))[0] == 410
    await alice.aclose()
    return f"created {code} via the queue, deduplicated, re-pointed and deleted it"


async def isolation_between_owners() -> str:
    alice, bob = await signed_in("alice"), await signed_in("bob")
    report = await created_via_stream_and_task(alice, f"https://example.com/e2e/{uuid.uuid4().hex}")
    link = report["link"]
    assert isinstance(link, dict)
    assert (await bob.get(f"/api/links/{link['id']}")).status_code == 404
    assert (await bob.get(f"/api/tasks/{report['task_id']}")).status_code == 404
    assert (await bob.delete(f"/api/links/{link['id']}")).status_code == 404
    admin = await signed_in("admin")
    listing = (await admin.get("/api/admin/links", params={"limit": 100})).json()
    assert link["id"] in {entry["id"] for entry in listing["links"]}
    assert (await alice.get("/api/admin/links")).status_code == 403
    for client in (alice, bob, admin):
        await client.aclose()
    return "another user sees neither the link nor the task; the admin sees it"


async def guest_sandbox() -> str:
    guest = await signed_in("guest")
    me = (await guest.get("/api/me")).json()
    assert me["is_guest"] is True, me
    links = (await guest.get("/api/links", params={"limit": 100})).json()["links"]
    codes = {entry["short_code"] for entry in links}
    assert {"Albert", "NanoGH"} <= codes, codes
    await guest.aclose()
    return f"the guest sees the {len(codes)} sandbox links"


async def input_rules() -> str:
    alice = await signed_in("alice")
    for bad_url in (
        "http://localhost/",
        "http://169.254.169.254/latest",
        "javascript:alert(1)",
        "http://mongo:27017/",
    ):
        answer = await alice.post("/api/links", json={"long_url": bad_url})
        assert (answer.status_code, answer.json()["error"]) == (422, "invalid_long_url"), (
            bad_url,
            answer.text,
        )
    await alice.aclose()
    return "private, internal and non-http destinations are refused"


async def main() -> int:
    failures = 0
    for step in (owner_lifecycle, isolation_between_owners, guest_sandbox, input_rules):
        try:
            sys.stdout.write(f"ok   {step.__name__}: {await step()}\n")
        except (AssertionError, httpx.HTTPError, KeyError, TimeoutError) as error:
            failures += 1
            sys.stdout.write(f"FAIL {step.__name__}: {error!r}\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
