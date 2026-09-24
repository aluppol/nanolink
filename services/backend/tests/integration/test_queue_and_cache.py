import uuid

import pytest
from nats.js.client import JetStreamContext
from redis.asyncio import Redis

from nanolink.adapters.mongo.connection import MongoDatabase
from nanolink.adapters.mongo.links import MongoLinks
from nanolink.adapters.mongo.tasks import MongoTaskLedger
from nanolink.adapters.nats.connection import RESULT_STREAM, TASK_STREAM, result_subject, task_subject
from nanolink.adapters.nats.messages import decode_result, decode_task
from nanolink.adapters.nats.publishers import JetStreamResultPublisher, JetStreamTaskQueue
from nanolink.adapters.short_codes import SecretsShortCodeGenerator
from nanolink.adapters.valkey.connection import link_cache_key
from nanolink.adapters.valkey.link_cache import ValkeyLinkCache
from nanolink.adapters.valkey.quota import ValkeyDailyQuota
from nanolink.application.batch_creation import BatchLinkCreation
from nanolink.domain.errors import QuotaExceeded
from nanolink.domain.tasks import CreateLinkTask, TaskStatus

pytestmark = pytest.mark.integration


async def test_tasks_are_stored_once_per_task_id(jetstream: JetStreamContext, owner_id: str) -> None:
    task = CreateLinkTask(f"task-{uuid.uuid4().hex}", owner_id, "https://example.com/q", None)
    queue = JetStreamTaskQueue(jetstream)
    await queue.enqueue(task)
    await queue.enqueue(task)
    subscription = await jetstream.subscribe(
        task_subject(owner_id), stream=TASK_STREAM, ordered_consumer=True
    )
    first = await subscription.next_msg(timeout=2)
    assert decode_task(first.data) == task
    with pytest.raises(TimeoutError):
        await subscription.next_msg(timeout=0.5)
    await subscription.unsubscribe()


async def test_a_batch_creates_links_and_publishes_results(
    gateway_database: MongoDatabase, jetstream: JetStreamContext, owner_id: str
) -> None:
    tasks = [
        CreateLinkTask(f"task-{uuid.uuid4().hex}", owner_id, f"https://example.com/b{i}", None)
        for i in range(3)
    ]
    links = MongoLinks(gateway_database)
    creation = BatchLinkCreation(
        links,
        SecretsShortCodeGenerator(),
        MongoTaskLedger(gateway_database),
        JetStreamResultPublisher(jetstream),
    )
    await creation.process([*tasks, tasks[0]])
    stored = await links.find_by_task_ids([task.task_id for task in tasks])
    subscription = await jetstream.subscribe(
        result_subject(owner_id), stream=RESULT_STREAM, ordered_consumer=True
    )
    results = [decode_result((await subscription.next_msg(timeout=2)).data) for _ in tasks]
    assert set(stored) == {task.task_id for task in tasks}
    assert {result.report.status for result in results if result is not None} == {TaskStatus.CREATED}
    await subscription.unsubscribe()
    await links.purge_owned(owner_id)


async def test_the_quota_counts_and_refunds(valkey: Redis, owner_id: str) -> None:
    quota = ValkeyDailyQuota(valkey)
    await quota.consume(owner_id, 2)
    await quota.consume(owner_id, 2)
    with pytest.raises(QuotaExceeded):
        await quota.consume(owner_id, 2)
    assert await quota.used_today(owner_id) == 2
    await quota.refund(owner_id)
    assert await quota.used_today(owner_id) == 1
    assert 0 < await valkey.ttl(f"quota:{owner_id}") <= 24 * 3600
    await valkey.delete(f"quota:{owner_id}")


async def test_forgetting_removes_cache_entries(valkey: Redis) -> None:
    await valkey.set(link_cache_key("Forget"), '{"state":"missing"}', ex=30)
    await ValkeyLinkCache(valkey).forget(["Forget", "Absent"])
    assert await valkey.exists(link_cache_key("Forget")) == 0
