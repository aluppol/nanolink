from collections.abc import AsyncIterator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

import httpx
from nats.aio.client import Client
from redis.asyncio import Redis

from nanolink.adapters.mongo.connection import MongoDatabase, mongo_database
from nanolink.adapters.mongo.links import MongoLinks
from nanolink.adapters.mongo.tasks import MongoTaskLedger
from nanolink.adapters.nats.connection import nats_connection
from nanolink.adapters.nats.publishers import JetStreamTaskQueue
from nanolink.adapters.oidc.jwks import JwksKeys
from nanolink.adapters.oidc.tokens import KeycloakTokenVerifier
from nanolink.adapters.valkey.connection import valkey_client
from nanolink.adapters.valkey.link_cache import ValkeyLinkCache
from nanolink.adapters.valkey.quota import ValkeyDailyQuota
from nanolink.application.link_creation import LinkCreationRequests
from nanolink.application.link_management import LinkModeration, OwnedLinkManagement
from nanolink.application.sandbox import DemoSandbox
from nanolink.application.task_reports import TaskReports
from nanolink.domain.ports import TokenVerifier
from nanolink.entrypoints.readiness import MongoReadiness, NatsReadiness, ReadinessCheck
from nanolink.entrypoints.settings import GatewaySettings


@dataclass(frozen=True, slots=True)
class GatewayServices:
    verifier: TokenVerifier
    creation_requests: LinkCreationRequests
    task_reports: TaskReports
    owned_links: OwnedLinkManagement
    moderation: LinkModeration
    sandbox: DemoSandbox
    readiness: Sequence[ReadinessCheck]
    public_base_url: str
    demo_reset_token: str


@asynccontextmanager
async def open_gateway_services(settings: GatewaySettings) -> AsyncIterator[GatewayServices]:
    async with AsyncExitStack() as stack:
        database = await stack.enter_async_context(mongo_database(settings.mongo))
        valkey = await stack.enter_async_context(valkey_client(settings.valkey))
        nats_client = await stack.enter_async_context(nats_connection(settings.nats))
        http = await stack.enter_async_context(httpx.AsyncClient())
        yield assemble_gateway(settings, database, valkey, nats_client, http)


def assemble_gateway(
    settings: GatewaySettings,
    database: MongoDatabase,
    valkey: Redis,
    nats_client: Client,
    http: httpx.AsyncClient,
) -> GatewayServices:
    links = MongoLinks(database)
    ledger = MongoTaskLedger(database)
    cache = ValkeyLinkCache(valkey)
    quota = ValkeyDailyQuota(valkey)
    keys = JwksKeys(http, settings.oidc.jwks_url)
    return GatewayServices(
        verifier=KeycloakTokenVerifier(keys, settings.oidc.issuer, settings.oidc.audience),
        creation_requests=LinkCreationRequests(JetStreamTaskQueue(nats_client.jetstream()), ledger, quota),
        task_reports=TaskReports(ledger, links),
        owned_links=OwnedLinkManagement(links, links, cache),
        moderation=LinkModeration(links, links, cache),
        sandbox=DemoSandbox(links, ledger, cache, quota),
        readiness=(MongoReadiness(database), NatsReadiness(nats_client)),
        public_base_url=settings.public_base_url,
        demo_reset_token=settings.demo_reset_token,
    )
