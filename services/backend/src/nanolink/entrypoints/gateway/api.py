from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from nanolink.domain.links import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageRequest
from nanolink.domain.tasks import TaskStatus, new_task_id
from nanolink.entrypoints.gateway.dependencies import Services
from nanolink.entrypoints.http_auth import CurrentPrincipal
from nanolink.entrypoints.http_views import (
    LinkPageView,
    LinkView,
    LongUrlBody,
    MeView,
    TaskAcceptedView,
    TaskView,
    link_page_view,
    link_view,
    me_view,
    task_view,
)

CURSOR_PATTERN = "^[0-9a-f]{24}$"

router = APIRouter(prefix="/api")

Cursor = Annotated[str | None, Query(pattern=CURSOR_PATTERN)]
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]


@router.get("/me")
async def read_me(principal: CurrentPrincipal, services: Services) -> MeView:
    created_today = await services.creation_requests.used_today(principal)
    return me_view(principal, created_today)


@router.post("/links", status_code=status.HTTP_202_ACCEPTED)
async def submit_link(
    body: LongUrlBody, response: Response, principal: CurrentPrincipal, services: Services
) -> TaskAcceptedView:
    task_id = new_task_id()
    await services.creation_requests.submit(principal, task_id, body.long_url)
    response.headers["Location"] = f"/api/tasks/{task_id}"
    return TaskAcceptedView(task_id=task_id, status=TaskStatus.QUEUED)


@router.get("/tasks/{task_id}")
async def read_task(task_id: str, principal: CurrentPrincipal, services: Services) -> TaskView:
    report = await services.task_reports.report(principal, task_id)
    return task_view(report, services.public_base_url)


@router.get("/links")
async def list_links(
    principal: CurrentPrincipal, services: Services, cursor: Cursor = None, limit: Limit = DEFAULT_PAGE_SIZE
) -> LinkPageView:
    page = await services.owned_links.list_page(principal, PageRequest(cursor, limit))
    return link_page_view(page, services.public_base_url)


@router.get("/links/{link_id}")
async def read_link(link_id: str, principal: CurrentPrincipal, services: Services) -> LinkView:
    link = await services.owned_links.read(principal, link_id)
    return link_view(link, services.public_base_url)


@router.patch("/links/{link_id}")
async def change_link(
    link_id: str, body: LongUrlBody, principal: CurrentPrincipal, services: Services
) -> LinkView:
    await services.owned_links.change_long_url(principal, link_id, body.long_url)
    link = await services.owned_links.read(principal, link_id)
    return link_view(link, services.public_base_url)


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(link_id: str, principal: CurrentPrincipal, services: Services) -> None:
    await services.owned_links.delete(principal, link_id)
