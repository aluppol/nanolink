from collections.abc import Collection, Mapping, Sequence

from pymongo import DESCENDING
from pymongo.errors import BulkWriteError, DuplicateKeyError

from nanolink.adapters.mongo.connection import (
    DUPLICATE_KEY_ERROR,
    LINKS_COLLECTION,
    Document,
    MongoDatabase,
    server_time,
)
from nanolink.adapters.mongo.documents import document_from_draft, link_from_document, object_id_or_none
from nanolink.domain.errors import DuplicateLongUrl
from nanolink.domain.links import Link, LinkDraft, LinkPage, PageRequest
from nanolink.domain.ports import OwnerUrl

ACTIVE: Document = {"deleted_at": None}


class MongoLinks:
    def __init__(self, database: MongoDatabase) -> None:
        self._database = database
        self._links = database[LINKS_COLLECTION]

    async def find_owned(self, link_id: str, owner_id: str) -> Link | None:
        object_id = object_id_or_none(link_id)
        if object_id is None:
            return None
        return await self._find_one({"_id": object_id, "owner_id": owner_id, **ACTIVE})

    async def find_any(self, link_id: str) -> Link | None:
        object_id = object_id_or_none(link_id)
        if object_id is None:
            return None
        return await self._find_one({"_id": object_id, **ACTIVE})

    async def list_owned(self, owner_id: str, page: PageRequest) -> LinkPage:
        return await self._page({"owner_id": owner_id, **ACTIVE}, page)

    async def list_all(self, page: PageRequest) -> LinkPage:
        return await self._page(dict(ACTIVE), page)

    async def change_long_url(self, link_id: str, long_url: str) -> None:
        object_id = object_id_or_none(link_id)
        if object_id is None:
            return
        try:
            await self._links.update_one(
                {"_id": object_id, **ACTIVE},
                {"$set": {"long_url": long_url}, "$currentDate": {"updated_at": True}},
            )
        except DuplicateKeyError as error:
            raise DuplicateLongUrl from error

    async def soft_delete(self, link_id: str) -> None:
        object_id = object_id_or_none(link_id)
        if object_id is None:
            return
        await self._links.update_one(
            {"_id": object_id, **ACTIVE},
            {"$currentDate": {"deleted_at": True, "updated_at": True}},
        )

    async def find_by_task_ids(self, task_ids: Collection[str]) -> Mapping[str, Link]:
        if not task_ids:
            return {}
        documents = await self._links.find({"task_id": {"$in": list(task_ids)}}).to_list()
        return {document["task_id"]: link_from_document(document) for document in documents}

    async def find_active_by_owner_urls(self, owner_urls: Collection[OwnerUrl]) -> Mapping[OwnerUrl, Link]:
        if not owner_urls:
            return {}
        clauses = [
            {"owner_id": owner_id, "long_url": long_url, **ACTIVE} for owner_id, long_url in owner_urls
        ]
        documents = await self._links.find({"$or": clauses}).to_list()
        return {
            (document["owner_id"], document["long_url"]): link_from_document(document)
            for document in documents
        }

    async def insert_drafts(self, drafts: Sequence[LinkDraft]) -> None:
        if not drafts:
            return
        now = await server_time(self._database)
        try:
            await self._links.insert_many(
                [document_from_draft(draft, now) for draft in drafts], ordered=False
            )
        except BulkWriteError as error:
            if not _only_duplicate_keys(error):
                raise

    async def count_owned(self, owner_id: str) -> int:
        return await self._links.count_documents({"owner_id": owner_id})

    async def short_codes_owned(self, owner_id: str) -> frozenset[str]:
        return frozenset(await self._links.distinct("short_code", {"owner_id": owner_id}))

    async def purge_owned(self, owner_id: str) -> None:
        await self._links.delete_many({"owner_id": owner_id})

    async def _find_one(self, criteria: Document) -> Link | None:
        document = await self._links.find_one(criteria)
        return None if document is None else link_from_document(document)

    async def _page(self, criteria: Document, page: PageRequest) -> LinkPage:
        query = {**criteria, **_after_cursor(page.cursor)}
        documents = await self._links.find(query).sort("_id", DESCENDING).limit(page.limit + 1).to_list()
        links = tuple(link_from_document(document) for document in documents[: page.limit])
        has_more = len(documents) > page.limit
        return LinkPage(links, links[-1].id if has_more else None)


def _after_cursor(cursor: str | None) -> Document:
    object_id = None if cursor is None else object_id_or_none(cursor)
    return {} if object_id is None else {"_id": {"$lt": object_id}}


def _only_duplicate_keys(error: BulkWriteError) -> bool:
    write_errors = error.details.get("writeErrors", [])
    concern_errors = error.details.get("writeConcernErrors", [])
    return not concern_errors and all(entry["code"] == DUPLICATE_KEY_ERROR for entry in write_errors)
