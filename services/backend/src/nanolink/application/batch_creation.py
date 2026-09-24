from collections.abc import Sequence
from contextlib import suppress

from nanolink.domain.errors import DependencyUnavailable
from nanolink.domain.links import Link, LinkDraft
from nanolink.domain.long_urls import long_url_problem
from nanolink.domain.ports import LinkFactory, ResultPublisher, ShortCodeGenerator, TaskLedger
from nanolink.domain.principals import is_owner_id
from nanolink.domain.tasks import (
    CREATION_ABANDONED,
    INVALID_OWNER,
    SHORT_CODES_EXHAUSTED,
    CreateLinkTask,
    TaskResult,
    created_result,
    failed_result,
)

MAX_INSERT_ATTEMPTS = 3


class BatchLinkCreation:
    def __init__(
        self,
        links: LinkFactory,
        codes: ShortCodeGenerator,
        ledger: TaskLedger,
        results: ResultPublisher,
    ) -> None:
        self._links = links
        self._codes = codes
        self._ledger = ledger
        self._results = results

    async def process(self, tasks: Sequence[CreateLinkTask]) -> None:
        unique_tasks = _unique_by_task_id(tasks)
        valid_tasks = [task for task in unique_tasks if task_problem(task) is None]
        links = await self._create(valid_tasks)
        results = [_result_for(task, links.get(task.task_id)) for task in unique_tasks]
        await self._ledger.record_reports([result.report for result in results])
        await self._results.publish(results)

    async def abandon(self, tasks: Sequence[CreateLinkTask]) -> None:
        abandoned = [failed_result(task, CREATION_ABANDONED) for task in _unique_by_task_id(tasks)]
        with suppress(DependencyUnavailable):
            await self._ledger.record_reports([result.report for result in abandoned])
        await self._results.publish(abandoned)

    async def _create(self, tasks: Sequence[CreateLinkTask]) -> dict[str, Link]:
        found: dict[str, Link] = {}
        remaining = list(tasks)
        for _ in range(MAX_INSERT_ATTEMPTS):
            found |= await self._existing(remaining)
            remaining = [task for task in remaining if task.task_id not in found]
            if not remaining:
                return found
            await self._links.insert_drafts([self._draft(task) for task in remaining])
        return found | await self._existing(remaining)

    async def _existing(self, tasks: Sequence[CreateLinkTask]) -> dict[str, Link]:
        if not tasks:
            return {}
        by_task = await self._links.find_by_task_ids([task.task_id for task in tasks])
        others = [task for task in tasks if task.task_id not in by_task]
        by_owner_url = await self._links.find_active_by_owner_urls({_owner_url(task) for task in others})
        reused = {
            task.task_id: by_owner_url[_owner_url(task)]
            for task in others
            if _owner_url(task) in by_owner_url
        }
        return {**by_task, **reused}

    def _draft(self, task: CreateLinkTask) -> LinkDraft:
        return LinkDraft(task.task_id, self._codes.next_code(), task.long_url, task.owner_id)


def _owner_url(task: CreateLinkTask) -> tuple[str, str]:
    return task.owner_id, task.long_url


def _unique_by_task_id(tasks: Sequence[CreateLinkTask]) -> list[CreateLinkTask]:
    return list({task.task_id: task for task in tasks}.values())


def task_problem(task: CreateLinkTask) -> str | None:
    if not is_owner_id(task.owner_id):
        return INVALID_OWNER
    return long_url_problem(task.long_url)


def _result_for(task: CreateLinkTask, link: Link | None) -> TaskResult:
    problem = task_problem(task)
    if problem is not None:
        return failed_result(task, problem)
    if link is None:
        return failed_result(task, SHORT_CODES_EXHAUSTED)
    return created_result(task, link)
