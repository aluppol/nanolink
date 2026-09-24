from dataclasses import dataclass

from nats.errors import TimeoutError as NatsTimeout

from nanolink.adapters.nats.inbox import JetStreamInbox
from tests.support import report_mismatches

BATCH_SIZE = 100
WAIT_SECONDS = 1.0
FETCHED = ["message-1", "message-2"]


@dataclass
class ScriptedSubscription:
    outcome: list[str] | Exception

    async def fetch(self, batch: int, **options: float) -> list[str]:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


CASES = [
    ("a fetch that finds messages returns them", FETCHED, FETCHED),
    ("the nats idle timeout is an empty batch", NatsTimeout(), []),
    ("the bare TimeoutError of an exhausted fetch deadline is an empty batch", TimeoutError(), []),
]


async def next_messages_after(outcome: list[str] | Exception) -> list[str] | str:
    inbox = JetStreamInbox(ScriptedSubscription(outcome), BATCH_SIZE, WAIT_SECONDS)
    try:
        return await inbox.next_messages()
    except Exception as error:
        return f"raised {error!r}"


async def test_inbox_returns_fetched_messages_and_an_empty_batch_on_every_timeout() -> None:
    mismatches = []
    for case_id, outcome, expected in CASES:
        actual = await next_messages_after(outcome)
        if actual != expected:
            mismatches.append(f"{case_id}: expected {expected}, got {actual}")
    report_mismatches(mismatches)
