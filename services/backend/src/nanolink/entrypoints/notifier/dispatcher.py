import asyncio
import logging

from nats.aio.msg import Msg

from nanolink.adapters.nats.inbox import JetStreamInbox, is_final_delivery
from nanolink.adapters.nats.messages import decode_result
from nanolink.application.notifications import CreatorNotifications
from nanolink.domain.errors import DependencyUnavailable

RETRY_PAUSE_SECONDS = 1.0

logger = logging.getLogger(__name__)


class EmailDispatcher:
    def __init__(self, inbox: JetStreamInbox, notifications: CreatorNotifications) -> None:
        self._inbox = inbox
        self._notifications = notifications

    async def dispatch_once(self) -> None:
        for message in await self._inbox.next_messages():
            await self._dispatch_safely(message)

    async def _dispatch_safely(self, message: Msg) -> None:
        try:
            await self._dispatch(message)
        except Exception:
            logger.exception("could not e-mail a result; it will be delivered again")

    async def _dispatch(self, message: Msg) -> None:
        result = decode_result(message.data)
        if result is None:
            await self._inbox.discard([message])
            return
        try:
            await self._notifications.notify(result)
        except DependencyUnavailable:
            await self._settle_failure(message)
            return
        await self._inbox.acknowledge([message])

    async def _settle_failure(self, message: Msg) -> None:
        if is_final_delivery(message):
            logger.warning("gave up e-mailing a result after the last delivery attempt")
            await self._inbox.discard([message])
            return
        await self._inbox.retry_later([message])


async def dispatch_forever(dispatcher: EmailDispatcher) -> None:
    while True:
        try:
            await dispatcher.dispatch_once()
        except Exception:
            logger.exception("e-mail dispatch failed; retrying")
            await asyncio.sleep(RETRY_PAUSE_SECONDS)
