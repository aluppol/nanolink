from dataclasses import dataclass
from datetime import datetime

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class Link:
    id: str
    short_code: str
    long_url: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class LinkDraft:
    task_id: str
    short_code: str
    long_url: str
    owner_id: str


@dataclass(frozen=True, slots=True)
class PageRequest:
    cursor: str | None
    limit: int


@dataclass(frozen=True, slots=True)
class LinkPage:
    links: tuple[Link, ...]
    next_cursor: str | None


def short_url_for(public_base_url: str, short_code: str) -> str:
    return f"{public_base_url.removesuffix('/')}/{short_code}"
