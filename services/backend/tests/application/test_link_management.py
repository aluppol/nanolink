from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from nanolink.application.link_management import LinkModeration, OwnedLinkManagement
from nanolink.domain.errors import DuplicateLongUrl, InvalidLongUrl, LinkNotFound, NotAuthorized
from nanolink.domain.links import LinkDraft, PageRequest
from tests.support import ADMIN, ALICE, BOB, InMemoryLinks, RecordingCache, report_mismatches

ALICE_A = LinkDraft("t-a", "AliceA", "https://example.com/a", ALICE.subject)
ALICE_B = LinkDraft("t-b", "AliceB", "https://example.com/b", ALICE.subject)
BOB_C = LinkDraft("t-c", "BobbyC", "https://example.com/c", BOB.subject)


@dataclass
class World:
    links: InMemoryLinks
    cache: RecordingCache
    owned: OwnedLinkManagement
    moderation: LinkModeration
    ids: dict[str, str]


def new_world() -> World:
    links, cache = InMemoryLinks(), RecordingCache()
    ids = {draft.short_code: links.add_active(draft).id for draft in (ALICE_A, ALICE_B, BOB_C)}
    return World(
        links, cache, OwnedLinkManagement(links, links, cache), LinkModeration(links, links, cache), ids
    )


Action = Callable[[World], Awaitable[object]]


@dataclass(frozen=True)
class Case:
    id: str
    action: Action
    error: type[Exception] | None
    active_codes: frozenset[str]
    forgotten: frozenset[str]


ALL = frozenset({"AliceA", "AliceB", "BobbyC"})


def change(principal_code: str, url: str) -> Action:
    return lambda world: world.owned.change_long_url(ALICE, world.ids[principal_code], url)


CASES = [
    Case("owner reads their link", lambda w: w.owned.read(ALICE, w.ids["AliceA"]), None, ALL, frozenset()),
    Case(
        "someone else's link is not found",
        lambda w: w.owned.read(ALICE, w.ids["BobbyC"]),
        LinkNotFound,
        ALL,
        frozenset(),
    ),
    Case(
        "an admin cannot use the owner API on others",
        lambda w: w.owned.read(ADMIN, w.ids["BobbyC"]),
        LinkNotFound,
        ALL,
        frozenset(),
    ),
    Case(
        "owner changes the target",
        change("AliceA", "https://example.com/new"),
        None,
        ALL,
        frozenset({"AliceA"}),
    ),
    Case("a new target is validated", change("AliceA", "http://10.0.0.1/"), InvalidLongUrl, ALL, frozenset()),
    Case(
        "a target already linked by the owner conflicts",
        change("AliceA", "https://example.com/b"),
        DuplicateLongUrl,
        ALL,
        frozenset(),
    ),
    Case(
        "owner deletes their link",
        lambda w: w.owned.delete(ALICE, w.ids["AliceA"]),
        None,
        frozenset({"AliceB", "BobbyC"}),
        frozenset({"AliceA"}),
    ),
    Case(
        "owner cannot delete others' links",
        lambda w: w.owned.delete(ALICE, w.ids["BobbyC"]),
        LinkNotFound,
        ALL,
        frozenset(),
    ),
    Case(
        "a user cannot moderate",
        lambda w: w.moderation.delete(BOB, w.ids["AliceA"]),
        NotAuthorized,
        ALL,
        frozenset(),
    ),
    Case(
        "an admin moderates any link",
        lambda w: w.moderation.delete(ADMIN, w.ids["BobbyC"]),
        None,
        frozenset({"AliceA", "AliceB"}),
        frozenset({"BobbyC"}),
    ),
    Case(
        "a user cannot list everything",
        lambda w: w.moderation.list_page(ALICE, PageRequest(None, 10)),
        NotAuthorized,
        ALL,
        frozenset(),
    ),
]


async def run_case(case: Case) -> str | None:
    world = new_world()
    try:
        await case.action(world)
        error = None
    except Exception as raised:
        error = type(raised)
    codes = frozenset(link.short_code for link in world.links.active_links())
    actual = (error, codes, frozenset(world.cache.forgotten))
    expected = (case.error, case.active_codes, case.forgotten)
    return None if actual == expected else f"{case.id}:\n  expected {expected}\n  got      {actual}"


async def test_link_management_rules() -> None:
    outcomes = [await run_case(case) for case in CASES]
    report_mismatches([outcome for outcome in outcomes if outcome is not None])


async def test_pages_run_newest_first_and_end_with_no_cursor() -> None:
    world = new_world()
    first = await world.moderation.list_page(ADMIN, PageRequest(None, 2))
    second = await world.moderation.list_page(ADMIN, PageRequest(first.next_cursor, 2))
    assert [link.short_code for link in first.links] == ["BobbyC", "AliceB"]
    assert [link.short_code for link in second.links] == ["AliceA"]
    assert second.next_cursor is None


async def test_owner_listing_shows_only_their_links() -> None:
    world = new_world()
    page = await world.owned.list_page(BOB, PageRequest(None, 10))
    assert [link.short_code for link in page.links] == ["BobbyC"]
