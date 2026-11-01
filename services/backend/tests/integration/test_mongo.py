import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pymongo.errors import OperationFailure, WriteError

from nanolink.adapters.mongo.connection import LINKS_COLLECTION, TASKS_COLLECTION, MongoDatabase
from nanolink.adapters.mongo.links import MongoLinks
from nanolink.adapters.mongo.tasks import MongoTaskLedger
from nanolink.domain.errors import DuplicateLongUrl
from nanolink.domain.links import LinkDraft, PageRequest
from nanolink.domain.tasks import CreateLinkTask, TaskReport, TaskStatus

pytestmark = pytest.mark.integration


def fresh_code() -> str:
    return uuid.uuid4().hex[:6]


def draft(owner_id: str, long_url: str, short_code: str | None = None) -> LinkDraft:
    return LinkDraft(f"task-{uuid.uuid4().hex}", short_code or fresh_code(), long_url, owner_id)


async def trust_seen_by_redirect(redirect_database: MongoDatabase, owner_id: str) -> dict[str, object]:
    documents = await (
        redirect_database[LINKS_COLLECTION]
        .find({"owner_id": owner_id}, {"_id": 0, "short_code": 1, "trusted": 1})
        .to_list()
    )
    return {document["short_code"]: document.get("trusted") for document in documents}


async def test_uniqueness_rules_hold_in_the_database(gateway_database: MongoDatabase, owner_id: str) -> None:
    links = MongoLinks(gateway_database)
    first = draft(owner_id, "https://example.com/unique")
    await links.insert_drafts([first])
    same_code = draft(owner_id, "https://example.com/other", first.short_code)
    same_url = draft(owner_id, "https://example.com/unique")
    same_task = LinkDraft(first.task_id, fresh_code(), "https://example.com/third", owner_id)
    await links.insert_drafts([same_code, same_url, same_task])
    stored = await links.find_by_task_ids([first.task_id, same_code.task_id, same_url.task_id])
    assert set(stored) == {first.task_id}
    await links.purge_owned(owner_id)


async def test_a_deleted_link_frees_its_long_url(gateway_database: MongoDatabase, owner_id: str) -> None:
    links = MongoLinks(gateway_database)
    original = draft(owner_id, "https://example.com/again")
    await links.insert_drafts([original])
    stored = (await links.find_by_task_ids([original.task_id]))[original.task_id]
    await links.soft_delete(stored.id)
    replacement = draft(owner_id, "https://example.com/again")
    await links.insert_drafts([replacement])
    active = await links.find_active_by_owner_urls({(owner_id, "https://example.com/again")})
    assert active[(owner_id, "https://example.com/again")].short_code == replacement.short_code
    await links.purge_owned(owner_id)


async def test_changing_to_an_owned_long_url_conflicts(
    gateway_database: MongoDatabase, owner_id: str
) -> None:
    links = MongoLinks(gateway_database)
    first, second = draft(owner_id, "https://example.com/1"), draft(owner_id, "https://example.com/2")
    await links.insert_drafts([first, second])
    stored = await links.find_by_task_ids([second.task_id])
    with pytest.raises(DuplicateLongUrl):
        await links.change_long_url(stored[second.task_id].id, "https://example.com/1", is_trusted=False)
    await links.purge_owned(owner_id)


async def test_timestamps_come_from_the_server_clock(gateway_database: MongoDatabase, owner_id: str) -> None:
    links = MongoLinks(gateway_database)
    created = draft(owner_id, "https://example.com/time")
    await links.insert_drafts([created])
    link = (await links.find_by_task_ids([created.task_id]))[created.task_id]
    assert link.created_at.tzinfo is not None
    assert abs(datetime.now(UTC) - link.created_at) < timedelta(minutes=5)
    await links.purge_owned(owner_id)


async def test_pages_are_newest_first(gateway_database: MongoDatabase, owner_id: str) -> None:
    links = MongoLinks(gateway_database)
    drafts = [draft(owner_id, f"https://example.com/page/{index}") for index in range(5)]
    for each in drafts:
        await links.insert_drafts([each])
    first = await links.list_owned(owner_id, PageRequest(None, 3))
    second = await links.list_owned(owner_id, PageRequest(first.next_cursor, 3))
    codes = [link.short_code for link in (*first.links, *second.links)]
    assert codes == [each.short_code for each in reversed(drafts)]
    assert second.next_cursor is None
    await links.purge_owned(owner_id)


async def test_trust_is_written_with_the_link_and_by_every_re_point(
    gateway_database: MongoDatabase, redirect_database: MongoDatabase, owner_id: str
) -> None:
    links = MongoLinks(gateway_database)
    by_admin = LinkDraft(
        f"task-{uuid.uuid4().hex}", fresh_code(), "https://example.com/a", owner_id, is_trusted=True
    )
    by_member = draft(owner_id, "https://example.com/m")
    await links.insert_drafts([by_admin, by_member])
    created = await trust_seen_by_redirect(redirect_database, owner_id)
    stored = await links.find_by_task_ids([by_admin.task_id, by_member.task_id])
    await links.change_long_url(stored[by_admin.task_id].id, "https://example.com/a2", is_trusted=False)
    await links.change_long_url(stored[by_member.task_id].id, "https://example.com/m", is_trusted=True)
    re_pointed = await trust_seen_by_redirect(redirect_database, owner_id)
    assert created == {by_admin.short_code: True, by_member.short_code: False}
    assert re_pointed == {by_admin.short_code: False, by_member.short_code: True}
    await links.purge_owned(owner_id)


async def test_trusted_is_optional_but_only_a_boolean(gateway_database: MongoDatabase, owner_id: str) -> None:
    now = datetime.now(UTC)
    document = {"long_url": "https://example.com/v", "owner_id": owner_id, "deleted_at": None}
    document |= {"created_at": now, "updated_at": now}
    await gateway_database[LINKS_COLLECTION].insert_one(
        {**document, "short_code": fresh_code(), "task_id": f"task-{uuid.uuid4().hex}"}
    )
    with pytest.raises(WriteError):
        await gateway_database[LINKS_COLLECTION].insert_one(
            {**document, "short_code": fresh_code(), "task_id": f"task-{uuid.uuid4().hex}", "trusted": "yes"}
        )
    assert await MongoLinks(gateway_database).count_owned(owner_id) == 1
    await MongoLinks(gateway_database).purge_owned(owner_id)


async def test_the_validator_rejects_malformed_documents(gateway_database: MongoDatabase) -> None:
    with pytest.raises(WriteError):
        await gateway_database[LINKS_COLLECTION].insert_one({"short_code": "bad code", "long_url": 42})


async def test_the_redirect_user_can_only_read(redirect_database: MongoDatabase) -> None:
    await redirect_database[LINKS_COLLECTION].find_one({"short_code": "nothing"})
    with pytest.raises(OperationFailure):
        await redirect_database[LINKS_COLLECTION].insert_one({"short_code": "abcdef"})


async def test_the_task_ledger_keeps_the_final_state(gateway_database: MongoDatabase, owner_id: str) -> None:
    ledger = MongoTaskLedger(gateway_database)
    task = CreateLinkTask(f"task-{uuid.uuid4().hex}", owner_id, "https://example.com/t", None)
    await ledger.record_reports([TaskReport(task.task_id, owner_id, TaskStatus.FAILED, None, "boom")])
    await ledger.record_queued(task)
    record = await ledger.find_owned(task.task_id, owner_id)
    assert record is not None
    assert (record.status, record.failure) == (TaskStatus.FAILED, "boom")
    assert await ledger.find_owned(task.task_id, "someone-else") is None
    indexes = await gateway_database[TASKS_COLLECTION].index_information()
    assert indexes["expire_after_retention"]["expireAfterSeconds"] == 7 * 24 * 3600
    await ledger.purge_owned(owner_id)
