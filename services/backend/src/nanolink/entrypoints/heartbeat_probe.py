import os
import sys
import time
from pathlib import Path

MAX_SILENCE_SECONDS = 60


def run() -> None:
    heartbeat = Path(os.environ.get("HEARTBEAT_FILE") or "/tmp/creator-heartbeat")
    try:
        silence = time.time() - heartbeat.stat().st_mtime
    except OSError:
        sys.exit(1)
    sys.exit(0 if silence < MAX_SILENCE_SECONDS else 1)


if __name__ == "__main__":
    run()
