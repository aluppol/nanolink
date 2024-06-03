import string
import random

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Depends
from services.database import get_database_service


class ShortUrlService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.get_collection("Urls")
        self.allowed_chars = string.digits + string.ascii_letters

    async def generate_short_url(self, owner_id: str) -> str:
        short_url = self.generate_random_string()
        is_short_url_in_db = await self.collection.find_one({short_url: short_url, owner_id: owner_id})
        while is_short_url_in_db:
            short_url = self.generate_random_string()
            is_short_url_in_db = await self.collection.find_one({short_url: short_url, owner_id: owner_id})

        return short_url

    def generate_random_string(self, length=6) -> str:
        return "".join(random.choices(self.allowed_chars, k=length))


def get_short_url_service(dbs=Depends(get_database_service)):
    return ShortUrlService(dbs.get_database())
