from collections.abc import Sequence

from nats.errors import Error as NatsError
from nats.js.client import JetStreamContext

from nanolink.adapters.nats.connection import PUBLISH_TIMEOUT_SECONDS, result_subject, task_subject
from nanolink.adapters.nats.messages import encode_result, encode_task
from nanolink.domain.errors import DependencyUnavailable
from nanolink.domain.tasks import CreateLinkTask, TaskResult

MESSAGE_ID_HEADER = "Nats-Msg-Id"


class JetStreamTaskQueue:
    def __init__(self, jetstream: JetStreamContext) -> None:
        self._jetstream = jetstream

    async def enqueue(self, task: CreateLinkTask) -> None:
        await _publish(self._jetstream, task_subject(task.owner_id), encode_task(task), task.task_id)


class JetStreamResultPublisher:
    def __init__(self, jetstream: JetStreamContext) -> None:
        self._jetstream = jetstream

    async def publish(self, results: Sequence[TaskResult]) -> None:
        for result in results:
            subject = result_subject(result.report.owner_id)
            await _publish(self._jetstream, subject, encode_result(result), result.report.task_id)


async def _publish(jetstream: JetStreamContext, subject: str, payload: bytes, message_id: str) -> None:
    try:
        await jetstream.publish(
            subject, payload, timeout=PUBLISH_TIMEOUT_SECONDS, headers={MESSAGE_ID_HEADER: message_id}
        )
    except NatsError as error:
        raise DependencyUnavailable from error
