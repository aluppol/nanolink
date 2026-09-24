import logging
from collections.abc import Sequence
from pathlib import Path

from nats.aio.msg import Msg
from nats.errors import Error as NatsError
from pymongo.errors import ConnectionFailure, PyMongoError

from nanolink.adapters.nats.inbox import JetStreamInbox, is_final_delivery
from nanolink.adapters.nats.messages import decode_task
from nanolink.application.batch_creation import BatchLinkCreation
from nanolink.domain.errors import DependencyUnavailable
from nanolink.domain.tasks import CreateLinkTask

TRANSIENT_ERRORS = (ConnectionFailure, NatsError, DependencyUnavailable)
PROCESSING_ERRORS = (PyMongoError, NatsError, DependencyUnavailable)

logger = logging.getLogger(__name__)

Delivery = tuple[Msg, CreateLinkTask]


class CreatorWorker:
    def __init__(self, inbox: JetStreamInbox, creation: BatchLinkCreation, heartbeat: Path) -> None:
        self._inbox = inbox
        self._creation = creation
        self._heartbeat = heartbeat

    async def work_once(self) -> None:
        messages = await self._inbox.next_messages()
        self._heartbeat.touch()
        if messages:
            await self._handle(messages)

    async def _handle(self, messages: Sequence[Msg]) -> None:
        decoded = [(message, decode_task(message.data)) for message in messages]
        await self._inbox.discard([message for message, task in decoded if task is None])
        deliveries = [(message, task) for message, task in decoded if task is not None]
        if not deliveries:
            return
        try:
            await self._creation.process([task for _, task in deliveries])
        except TRANSIENT_ERRORS:
            logger.warning("a backing service failed; %d create tasks will be retried", len(deliveries))
            await self._retry_or_abandon(deliveries)
            return
        except PyMongoError:
            logger.exception("a batch of %d create tasks failed; retrying them one by one", len(deliveries))
            await self._isolate(deliveries)
            return
        await self._inbox.acknowledge([message for message, _ in deliveries])

    async def _isolate(self, deliveries: Sequence[Delivery]) -> None:
        for delivery in deliveries:
            await self._handle_alone(delivery)

    async def _handle_alone(self, delivery: Delivery) -> None:
        message, task = delivery
        try:
            await self._creation.process([task])
        except PROCESSING_ERRORS:
            await self._retry_or_abandon([delivery])
            return
        await self._inbox.acknowledge([message])

    async def _retry_or_abandon(self, deliveries: Sequence[Delivery]) -> None:
        final = [(message, task) for message, task in deliveries if is_final_delivery(message)]
        await self._inbox.retry_later(
            [message for message, _ in deliveries if not is_final_delivery(message)]
        )
        if final:
            await self._creation.abandon([task for _, task in final])
            await self._inbox.discard([message for message, _ in final])
