import os
import statistics
import sys
import time

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://web:8080")
SHORT_CODE = os.environ.get("SHORT_CODE", "Albert")
WARM_UP_REQUESTS = 200
MEASURED_REQUESTS = int(os.environ.get("REQUESTS", "2000"))


def timed_redirect(client: httpx.Client) -> float:
    started = time.perf_counter()
    response = client.get(f"/{SHORT_CODE}")
    elapsed_ms = (time.perf_counter() - started) * 1000
    if response.status_code != 302:
        raise SystemExit(f"expected a 302, got {response.status_code}")
    return elapsed_ms


def percentile(ordered: list[float], share: float) -> float:
    return ordered[max(int(share * len(ordered)) - 1, 0)]


def describe(samples: list[float], elapsed: float) -> str:
    rate = MEASURED_REQUESTS / elapsed
    spread = ", ".join(
        f"p{round(share * 100)} {percentile(samples, share):.2f} ms" for share in (0.5, 0.9, 0.99)
    )
    return (
        f"{MEASURED_REQUESTS} sequential redirects on one connection: {rate:.0f} req/s, "
        f"mean {statistics.mean(samples):.2f} ms, {spread}, max {samples[-1]:.2f} ms\n"
    )


def main() -> int:
    with httpx.Client(base_url=BASE_URL, follow_redirects=False, timeout=10) as client:
        for _ in range(WARM_UP_REQUESTS):
            timed_redirect(client)
        started = time.perf_counter()
        samples = sorted(timed_redirect(client) for _ in range(MEASURED_REQUESTS))
        elapsed = time.perf_counter() - started
    summary = describe(samples, elapsed)
    sys.stdout.write(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
