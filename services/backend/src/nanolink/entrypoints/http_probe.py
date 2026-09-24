import os
import sys
import urllib.request
from urllib.error import URLError

PROBE_TIMEOUT_SECONDS = 3


def run() -> None:
    port = os.environ.get("PORT") or "8000"
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/healthz", timeout=PROBE_TIMEOUT_SECONDS
        ) as reply:
            sys.exit(0 if reply.status == 200 else 1)
    except (URLError, OSError):
        sys.exit(1)


if __name__ == "__main__":
    run()
