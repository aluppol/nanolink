from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from nanolink.domain.links import Link, LinkPage, short_url_for
from nanolink.domain.principals import Principal
from nanolink.domain.tasks import TaskReport, TaskStatus


class View(BaseModel):
    model_config = ConfigDict(frozen=True)


class LongUrlBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    long_url: str = Field(max_length=8192)


class LinkView(View):
    id: str
    short_code: str
    short_url: str
    long_url: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class LinkPageView(View):
    links: list[LinkView]
    next_cursor: str | None


class TaskAcceptedView(View):
    task_id: str
    status: TaskStatus


class TaskView(View):
    task_id: str
    status: TaskStatus
    link: LinkView | None
    failure: str | None


class MeView(View):
    user_id: str
    username: str
    roles: list[str]
    is_guest: bool
    is_admin: bool
    daily_quota: int | None
    created_today: int


class DemoResetView(View):
    removed: int
    seeded: int


class ErrorView(View):
    error: str
    message: str


def link_view(link: Link, public_base_url: str) -> LinkView:
    return LinkView(
        id=link.id,
        short_code=link.short_code,
        short_url=short_url_for(public_base_url, link.short_code),
        long_url=link.long_url,
        owner_id=link.owner_id,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def link_page_view(page: LinkPage, public_base_url: str) -> LinkPageView:
    return LinkPageView(
        links=[link_view(link, public_base_url) for link in page.links], next_cursor=page.next_cursor
    )


def task_view(report: TaskReport, public_base_url: str) -> TaskView:
    link = None if report.link is None else link_view(report.link, public_base_url)
    return TaskView(task_id=report.task_id, status=report.status, link=link, failure=report.failure)


def me_view(principal: Principal, created_today: int) -> MeView:
    return MeView(
        user_id=principal.subject,
        username=principal.username,
        roles=sorted(role.value for role in principal.roles),
        is_guest=principal.is_guest,
        is_admin=principal.is_admin,
        daily_quota=principal.daily_quota,
        created_today=created_today,
    )
