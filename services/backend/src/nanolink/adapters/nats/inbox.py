from collections.abc import Sequence

from nats.aio.msg import Msg
from nats.errors import TimeoutError as NatsTimeout
from nats.js.client import JetStreamContext

MAX_DELIVERIES = 6
RETRY_DELAYS_SECONDS = (2.0, 10.0, 30.0, 60.0, 120.0)


class JetStreamInbox:
    def __init__(
        self, subscription: JetStreamContext.PullSubscription, batch_size: int, wait_seconds: float
    ) -> None:
        self._subscription = subscription
        self._batch_size = batch_size
        self._wait_seconds = wait_seconds

    async def next_messages(self) -> list[Msg]:
        try:
            return await self._subscription.fetch(self._batch_size, timeout=self._wait_seconds)
        except NatsTimeout:
            return []

    async def acknowledge(self, messages: Sequence[Msg]) -> None:
        for message in messages:
            await message.ack()

    async def retry_later(self, messages: Sequence[Msg]) -> None:
        for message in messages:
            await message.nak(delay=retry_delay(message.metadata.num_delivered))

    async def discard(self, messages: Sequence[Msg]) -> None:
        for message in messages:
            await message.term()


def retry_delay(deliveries: int) -> float:
    index = min(max(deliveries, 1), len(RETRY_DELAYS_SECONDS)) - 1
    return RETRY_DELAYS_SECONDS[index]


def is_final_delivery(message: Msg) -> bool:
    return message.metadata.num_delivered >= MAX_DELIVERIES
