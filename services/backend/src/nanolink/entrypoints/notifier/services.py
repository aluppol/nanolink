import asyncio
from collections.abc import AsyncIterator, Coroutine, Sequence
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any

import httpx
from nats.aio.client import Client
from nats.aio.msg import Msg

from nanolink.adapters.email.senders import DisabledEmailSender, SmtpEmailSender
from nanolink.adapters.nats.connection import (
    NOTIFIER_CONSUMER,
    RESULT_STREAM,
    RESULT_SUBJECTS,
    nats_connection,
)
from nanolink.adapters.nats.inbox import JetStreamInbox
from nanolink.adapters.nats.messages import decode_result
from nanolink.adapters.oidc.jwks import JwksKeys
from nanolink.adapters.oidc.tokens import KeycloakTokenVerifier
from nanolink.application.notifications import CreatorNotifications
from nanolink.domain.ports import EmailSender, TokenVerifier
from nanolink.entrypoints.notifier.dispatcher import EmailDispatcher, dispatch_forever
from nanolink.entrypoints.notifier.feed import LiveFeed
from nanolink.entrypoints.readiness import NatsReadiness, ReadinessCheck
from nanolink.entrypoints.settings import NotifierSettings

EMAIL_BATCH_SIZE = 20
EMAIL_WAIT_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class NotifierServices:
    verifier: TokenVerifier
    feed: LiveFeed
    readiness: Sequence[ReadinessCheck]
    public_base_url: str


@asynccontextmanager
async def open_notifier_services(settings: NotifierSettings) -> AsyncIterator[NotifierServices]:
    async with AsyncExitStack() as stack:
        nats_client = await stack.enter_async_context(nats_connection(settings.nats))
        http = await stack.enter_async_context(httpx.AsyncClient())
        feed = LiveFeed()
        await stack.enter_async_context(live_subscription(nats_client, feed))
        dispatcher = await email_dispatcher(settings, nats_client)
        await stack.enter_async_context(background(dispatch_forever(dispatcher)))
        keys = JwksKeys(http, settings.oidc.jwks_url)
        verifier = KeycloakTokenVerifier(keys, settings.oidc.issuer, settings.oidc.audience)
        yield NotifierServices(verifier, feed, (NatsReadiness(nats_client),), settings.public_base_url)


@asynccontextmanager
async def live_subscription(nats_client: Client, feed: LiveFeed) -> AsyncIterator[None]:
    async def deliver(message: Msg) -> None:
        result = decode_result(message.data)
        if result is not None:
            feed.publish(result.report)

    subscription = await nats_client.subscribe(RESULT_SUBJECTS, cb=deliver)
    try:
        yield
    finally:
        with suppress(Exception):
            await subscription.unsubscribe()


@asynccontextmanager
async def background(work: Coroutine[Any, Any, None]) -> AsyncIterator[None]:
    task = asyncio.create_task(work)
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def email_dispatcher(settings: NotifierSettings, nats_client: Client) -> EmailDispatcher:
    subscription = await nats_client.jetstream().pull_subscribe_bind(
        durable=NOTIFIER_CONSUMER, stream=RESULT_STREAM
    )
    inbox = JetStreamInbox(subscription, EMAIL_BATCH_SIZE, EMAIL_WAIT_SECONDS)
    return EmailDispatcher(inbox, CreatorNotifications(email_sender(settings), settings.public_base_url))


def email_sender(settings: NotifierSettings) -> EmailSender:
    if settings.smtp is None:
        return DisabledEmailSender()
    return SmtpEmailSender(settings.smtp)
