from datetime import datetime
from pymongo import ReturnDocument
from typing import List
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Depends
from bson import ObjectId

from services.database import get_database_service
from services.short_url_service import ShortUrlService, get_short_url_service
from services.http_service import HTTPService, get_http_service
from schemas import UrlCreate, Url


class UrlAlreadyExistsException(Exception):
    def __init__(self, url: str):
        super().__init__(f"Url {url} already exists for the client")


class UrlNotValidException(Exception):
    def __init__(self, url: str, description: str):
        super().__init__(f"Url {url} cannot be followed: {description}")


class UrlService:
    def __init__(self,
                 db: AsyncIOMotorClient,
                 sus: ShortUrlService,
                 https: HTTPService):
        self.collection = db.get_collection("Urls")
        self.sus = sus
        self.https = https

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def validate_url(self, url: str):
        """
        Validates a URL by sending an HTTP GET request.

        Args:
            url (str): The URL to validate.

        Raises:
            UrlNotValidException: If the URL is not valid (response status is 400 or higher)
                or there is a client-side error.
        """
        try:
            response = await self.https.fetch_url(url)
            if response.status >= 400:
                raise UrlNotValidException(url, response.reason)
        except aiohttp.ClientError as e:
            raise UrlNotValidException(url, str(e))

    async def create(self, url_payload: UrlCreate, owner_id: str) -> Url:
        """
        Creates a short URL for a given long URL and owner ID.

        Args:
            url_payload (UrlCreate): The payload containing the long URL to shorten.
            owner_id (str): The ID of the owner of the URL.

        Returns:
            Url: The created URL object containing the short URL, long URL, owner ID, and creation date.

        Raises:
            UrlNotValidException: If the long URL is not valid.
            UrlAlreadyExistsException: If the long URL already exists in the database for the given owner.
        """
        long_url = url_payload.long_url
        await self.validate_url(long_url)

        is_long_url_in_db = await self.collection.find_one({long_url: long_url, owner_id: owner_id})
        if is_long_url_in_db:
            raise UrlAlreadyExistsException(long_url)

        short_url = await self.sus.generate_short_url(owner_id)
        url = {
            **url_payload.dict(exclude_unset=True),
            "short_url": short_url,
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
        """
        Updates an existing URL document.

        Args:
            url_id (ObjectId): The ID of the URL document to update.
            url_payload (UrlCreate): The payload containing the new long URL.
            owner_id (str): The ID of the owner of the URL.
            include_deleted (bool): Whether to include deleted URLs in the query. Defaults to False.

        Returns:
            Optional[Url]: The updated URL object, or None if the URL was not found.

        Raises:
            UrlNotValidException: If the long URL is not valid.
            UrlAlreadyExistsException: If the long URL already exists in the database for the given owner.
        """
        long_url = url_payload.long_url
        await self.validate_url(long_url)

        is_long_url_in_db = await self.collection.find_one({long_url: long_url, owner_id: owner_id})
        if is_long_url_in_db:
            raise UrlAlreadyExistsException(long_url)

        update_data = {
            **url_payload.dict(exclude_unset=True),
            "updated_at": datetime.now(),
        }

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


async def get_url_service(
        dbs=Depends(get_database_service),
        sus=Depends(get_short_url_service),
        https=Depends(get_http_service),
):
    return UrlService(dbs.get_database(), sus, https)
