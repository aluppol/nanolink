import sys

import httpx

BASE_URL = "http://web:8080"

Check = tuple[str, str, dict[str, str], int, dict[str, str]]

CHECKS: list[Check] = [
    ("liveness", "/healthz", {}, 200, {}),
    (
        "user interface",
        "/",
        {},
        200,
        {"content-type": "text/html", "content-security-policy": "default-src 'self'"},
    ),
    ("API without a token", "/api/me", {}, 401, {"www-authenticate": "Bearer"}),
    ("API with a forged token", "/api/me", {"X-Forwarded-Access-Token": "forged"}, 401, {}),
    (
        "seeded short link",
        "/Albert",
        {},
        302,
        {"location": "https://albert.luppol.com/", "cache-control": "no-store"},
    ),
    (
        "seeded short link again, from the cache",
        "/Albert",
        {},
        302,
        {"location": "https://albert.luppol.com/"},
    ),
    (
        "seeded short link for a browser",
        "/NanoGH",
        {"Accept": "text/html"},
        302,
        {"location": "https://github.com/aluppol/nanolink"},
    ),
    ("unknown short link", "/zzzzzz", {}, 404, {"content-type": "application/json"}),
    (
        "unknown short link for a browser",
        "/zzzzzz",
        {"Accept": "text/html"},
        404,
        {"content-type": "text/html"},
    ),
    ("login gateway paths are not the app's", "/oauth2/start", {}, 404, {}),
    ("internal endpoints are not routed", "/internal/demo-reset", {}, 404, {}),
    ("readiness is not public", "/readyz", {}, 404, {}),
]


def failure_of(client: httpx.Client, check: Check) -> str | None:
    name, path, headers, status, expected = check
    response = client.get(path, headers=headers)
    problems = [f"status {response.status_code}, expected {status}"] if response.status_code != status else []
    problems += [
        f"{header} is {response.headers.get(header)!r}, expected it to contain {value!r}"
        for header, value in expected.items()
        if value not in response.headers.get(header, "")
    ]
    return f"{name} ({path}): {'; '.join(problems)}" if problems else None


def main() -> int:
    with httpx.Client(base_url=BASE_URL, follow_redirects=False, timeout=10) as client:
        failures = [failure for check in CHECKS if (failure := failure_of(client, check)) is not None]
    for failure in failures:
        sys.stdout.write(f"::error title=smoke::{failure}\n")
    sys.stdout.write(f"smoke: {len(CHECKS) - len(failures)}/{len(CHECKS)} checks passed\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
