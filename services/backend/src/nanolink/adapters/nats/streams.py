from nats.js.api import (
    AckPolicy,
    ConsumerConfig,
    DeliverPolicy,
    DiscardPolicy,
    RetentionPolicy,
    StorageType,
    StreamConfig,
)
from nats.js.client import JetStreamContext
from nats.js.errors import NotFoundError

from nanolink.adapters.nats.connection import (
    CREATOR_CONSUMER,
    NOTIFIER_CONSUMER,
    RESULT_STREAM,
    RESULT_SUBJECTS,
    TASK_STREAM,
    TASK_SUBJECTS,
)
from nanolink.adapters.nats.inbox import MAX_DELIVERIES

DAY_SECONDS = 24 * 3600
DUPLICATE_WINDOW_SECONDS = 120
ACK_WAIT_SECONDS = 30

TASK_STREAM_CONFIG = StreamConfig(
    name=TASK_STREAM,
    subjects=[TASK_SUBJECTS],
    retention=RetentionPolicy.LIMITS,
    storage=StorageType.FILE,
    discard=DiscardPolicy.OLD,
    max_age=7 * DAY_SECONDS,
    max_bytes=256 * 1024 * 1024,
    duplicate_window=DUPLICATE_WINDOW_SECONDS,
    num_replicas=1,
)

RESULT_STREAM_CONFIG = StreamConfig(
    name=RESULT_STREAM,
    subjects=[RESULT_SUBJECTS],
    retention=RetentionPolicy.LIMITS,
    storage=StorageType.FILE,
    discard=DiscardPolicy.OLD,
    max_age=DAY_SECONDS,
    max_bytes=64 * 1024 * 1024,
    duplicate_window=DUPLICATE_WINDOW_SECONDS,
    num_replicas=1,
)


def durable_consumer(name: str, subjects: str) -> ConsumerConfig:
    return ConsumerConfig(
        durable_name=name,
        ack_policy=AckPolicy.EXPLICIT,
        deliver_policy=DeliverPolicy.ALL,
        ack_wait=ACK_WAIT_SECONDS,
        max_deliver=MAX_DELIVERIES,
        max_ack_pending=1000,
        filter_subject=subjects,
    )


async def migrate_streams(jetstream: JetStreamContext) -> None:
    await _ensure_stream(jetstream, TASK_STREAM_CONFIG)
    await _ensure_stream(jetstream, RESULT_STREAM_CONFIG)
    await jetstream.add_consumer(TASK_STREAM, durable_consumer(CREATOR_CONSUMER, TASK_SUBJECTS))
    await jetstream.add_consumer(RESULT_STREAM, durable_consumer(NOTIFIER_CONSUMER, RESULT_SUBJECTS))


async def _ensure_stream(jetstream: JetStreamContext, config: StreamConfig) -> None:
    try:
        await jetstream.stream_info(str(config.name))
    except NotFoundError:
        await jetstream.add_stream(config)
        return
    await jetstream.update_stream(config)
