import os
from motor.motor_asyncio import AsyncIOMotorClient

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", 27017)
DB_NAME = os.getenv("DB_NAME")

# Construct the MongoDB URI
MONGO_DETAILS = f"mongodb://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

client = AsyncIOMotorClient(MONGO_DETAILS)

db = client[DB_NAME]


def get_database():
    return db
