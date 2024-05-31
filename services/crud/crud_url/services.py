from datetime import datetime
from pymongo import ReturnDocument
from typing import List
from bson import ObjectId

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from fastapi import Depends
from .database import get_database
from .schemas import UrlCreate, Url


class ShortUrlService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def generate_short_url(self, long_url: str, owner_id: str) -> str:    # TODO
        return 'my_short_url'


def get_short_url_service(db=Depends(get_database)):
    return ShortUrlService(db)


class UrlService:
    def __init__(self,
                 db: AsyncIOMotorClient,
                 sus: ShortUrlService):
        self.collection = db.get_collection("Urls")
        self.sus = sus

    async def create(self, url_payload: UrlCreate, owner_id: str) -> Url:
        short_url = await self.sus.generate_short_url(url_payload.long_url, owner_id)
        url = {
            "short_url": short_url,
            "long_url": url_payload.long_url,
            "owner_id": owner_id,
            "created_at": datetime.now(),
        }

        result = await self.collection.insert_one(url)
        url['_id'] = result.inserted_id
        return Url(**url)

    async def read(self, url_id: ObjectId, owner_id: str, include_deleted=False) -> Url:
        query = {
            '_id': url_id,
            'owner_id': owner_id,
        }

        if not include_deleted:
            query['deleted_at'] = None

        result = await self.collection.find_one(query)
        return Url(**result) if result else None

    async def read_all(self, owner_id: str, include_deleted=False) -> List[Url]:
        query = {
            'owner_id': owner_id,
        }

        if not include_deleted:
            query['deleted_at'] = None

        result = []

        async for url in self.collection.find(query):
            result.append(Url(**url))

        return result

    async def update(self, url_id: ObjectId,  url_payload: UrlCreate, owner_id: str, include_deleted=False) -> Url:
        short_url = await self.sus.generate_short_url(url_payload.long_url, owner_id)
        update_data = url_payload.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.now()
        update_data['short_url'] = short_url

        query = {"_id": url_id, "owner_id": owner_id}
        if not include_deleted:
            query["deleted_at"] = None

        result = await self.collection.find_one_and_update(
            query,
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )

        return Url(**result) if result else None

    async def delete(self, url_id: ObjectId, owner_id: str) -> bool:
        result = await self.collection.update_one(
            {'_id': url_id, 'owner_id': owner_id},
            {"$set": {"deleted_at": datetime.now()}}
        )

        return result.modified_count > 0


def get_url_service(db=Depends(get_database), sus=Depends(get_short_url_service)):
    return UrlService(db, sus)
