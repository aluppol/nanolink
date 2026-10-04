from dataclasses import dataclass

from nanolink.domain.principals import GUEST_DAILY_QUOTA, USER_DAILY_QUOTA, Principal, Role, is_owner_id
from nanolink.domain.sandbox import SANDBOX_OWNER_ID
from tests.support import ADMIN, ALICE, GUEST, GUEST_IN_SESSION, report_mismatches


@dataclass(frozen=True)
class Case:
    id: str
    principal: Principal
    owner_id: str
    quota_holder: str
    daily_quota: int | None
    is_admin: bool
    is_guest: bool
    notify_email: str | None


ADMIN_WHO_IS_ALSO_GUEST = Principal(
    "mixed-0005", "mixed", "m@example.org", frozenset({Role.ADMIN, Role.GUEST})
)

CASES = [
    Case(
        "user owns their links",
        ALICE,
        ALICE.subject,
        ALICE.subject,
        USER_DAILY_QUOTA,
        is_admin=False,
        is_guest=False,
        notify_email=ALICE.email,
    ),
    Case(
        "admin has no quota",
        ADMIN,
        ADMIN.subject,
        ADMIN.subject,
        None,
        is_admin=True,
        is_guest=False,
        notify_email=None,
    ),
    Case(
        "guest works in the sandbox, counted by subject without a session",
        GUEST,
        SANDBOX_OWNER_ID,
        "guest-guest-0004",
        GUEST_DAILY_QUOTA,
        is_admin=False,
        is_guest=True,
        notify_email=None,
    ),
    Case(
        "guest in a session is counted per session",
        GUEST_IN_SESSION,
        SANDBOX_OWNER_ID,
        "guest-session-1",
        GUEST_DAILY_QUOTA,
        is_admin=False,
        is_guest=True,
        notify_email=None,
    ),
    Case(
        "guest role wins over admin",
        ADMIN_WHO_IS_ALSO_GUEST,
        SANDBOX_OWNER_ID,
        "guest-mixed-0005",
        GUEST_DAILY_QUOTA,
        is_admin=False,
        is_guest=True,
        notify_email=None,
    ),
]


def test_principal_rules() -> None:
    mismatches = []
    for case in CASES:
        actual = (
            case.principal.owner_id,
            case.principal.quota_holder,
            case.principal.daily_quota,
            case.principal.is_admin,
            case.principal.is_guest,
            case.principal.notify_email,
        )
        expected = (
            case.owner_id,
            case.quota_holder,
            case.daily_quota,
            case.is_admin,
            case.is_guest,
            case.notify_email,
        )
        if actual != expected:
            mismatches.append(f"{case.id}: expected {expected}, got {actual}")
    report_mismatches(mismatches)


OWNER_ID_CASES = [
    ("keycloak uuid", "5f0c1f6e-8a3b-4c2d-9e1f-0a1b2c3d4e5f", True),
    ("sandbox", "sandbox", True),
    ("empty", "", False),
    ("dot would split a subject", "a.b", False),
    ("wildcard", "a*", False),
    ("65 characters", "a" * 65, False),
]


def test_owner_id_format() -> None:
    mismatches = [
        f"{case_id}: expected {expected}, got {not expected}"
        for case_id, candidate, expected in OWNER_ID_CASES
        if is_owner_id(candidate) != expected
    ]
    report_mismatches(mismatches)
