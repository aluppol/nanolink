from nanolink.domain.links import Link, short_url_for
from nanolink.domain.notifications import EmailMessage, email_for
from nanolink.domain.sandbox import DEMO_LINK_SEEDS, seed_drafts
from nanolink.domain.short_codes import is_reserved_short_code, is_short_code
from nanolink.domain.tasks import TaskReport, TaskResult, TaskStatus
from tests.support import FIXED_TIME, report_mismatches

SHORT_CODE_CASES = [
    ("six letters and digits", "aB3xY9", True),
    ("five characters", "aB3xY", False),
    ("seven characters", "aB3xY9z", False),
    ("punctuation", "aB3-Y9", False),
    ("non-ASCII letter", "aB3xYé", False),
]

RESERVED_CASES = [
    ("assets route", "assets", True),
    ("oauth2 route", "oauth2", True),
    ("readyz route", "readyz", True),
    ("a demo seed", DEMO_LINK_SEEDS[0].short_code, True),
    ("an ordinary code", "aB3xY9", False),
]


def test_short_code_rules() -> None:
    mismatches = [
        f"{case_id}: is_short_code should be {expected}"
        for case_id, candidate, expected in SHORT_CODE_CASES
        if is_short_code(candidate) != expected
    ]
    mismatches += [
        f"{case_id}: is_reserved_short_code should be {expected}"
        for case_id, candidate, expected in RESERVED_CASES
        if is_reserved_short_code(candidate) != expected
    ]
    mismatches += [
        f"seed {draft.short_code} is not a valid code"
        for draft in seed_drafts()
        if not is_short_code(draft.short_code)
    ]
    report_mismatches(mismatches)


LINK = Link("0" * 24, "aB3xY9", "https://example.com/", "alice-0001", FIXED_TIME, FIXED_TIME)
CREATED = TaskReport("t1", "alice-0001", TaskStatus.CREATED, LINK, None)
FAILED = TaskReport(
    "t2", "alice-0001", TaskStatus.FAILED, None, "no free short code was found; please try again"
)
BASE = "https://nanolink.luppol.com/"

EMAIL_CASES = [
    (
        "created, with address",
        TaskResult(CREATED, "a@example.org"),
        EmailMessage(
            "a@example.org",
            "Your NanoLink is ready",
            "Your short link is ready: https://nanolink.luppol.com/aB3xY9\nIt redirects to: https://example.com/\n",
        ),
    ),
    (
        "failed, with address",
        TaskResult(FAILED, "a@example.org"),
        EmailMessage(
            "a@example.org",
            "NanoLink could not create your link",
            "NanoLink could not create your link: no free short code was found; please try again\n",
        ),
    ),
    ("no address", TaskResult(CREATED, None), None),
]


def test_email_composition() -> None:
    mismatches = [
        f"{case_id}: expected {expected}, got {actual}"
        for case_id, result, expected in EMAIL_CASES
        if (actual := email_for(result, BASE)) != expected
    ]
    if short_url_for(BASE, "aB3xY9") != "https://nanolink.luppol.com/aB3xY9":
        mismatches.append("short_url_for must not double the slash")
    report_mismatches(mismatches)
