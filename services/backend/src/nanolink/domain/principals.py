import re
from dataclasses import dataclass
from enum import StrEnum

from nanolink.domain.sandbox import SANDBOX_OWNER_ID


class Role(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"
    GUEST = "guest"


GUEST_DAILY_QUOTA = 25
USER_DAILY_QUOTA = 200

_OWNER_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")


def is_owner_id(candidate: str) -> bool:
    return _OWNER_ID_PATTERN.fullmatch(candidate) is not None


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    username: str
    email: str | None
    roles: frozenset[Role]

    @property
    def is_guest(self) -> bool:
        return Role.GUEST in self.roles

    @property
    def is_admin(self) -> bool:
        return Role.ADMIN in self.roles and not self.is_guest

    @property
    def owner_id(self) -> str:
        return SANDBOX_OWNER_ID if self.is_guest else self.subject

    @property
    def daily_quota(self) -> int | None:
        if self.is_admin:
            return None
        return GUEST_DAILY_QUOTA if self.is_guest else USER_DAILY_QUOTA

    @property
    def notify_email(self) -> str | None:
        return None if self.is_guest else self.email
