import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", 27017)
DB_NAME = os.getenv("DB_NAME")


class DatabaseService:
    def __init__(self, db_user: str, db_pass: str, db_host: str, db_port: str, db_name: str):
        # Construct the MongoDB URI
        self.db_uri = f"mongodb://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        self.db_name = db_name
        self.client = None
        self.db = None

    async def connect(self, retries=5, delay=10):
        for attempt in range(1, retries + 1):
            try:
                self.client = AsyncIOMotorClient(self.db_uri)
                self.db = self.client[self.db_name]
                # The first operation that actually initiates a connection attempt
                await self.db.command("ping")
                print("Connected to the database successfully.")
                return
            except Exception as e:
                print(f"Attempt {attempt}: Error connecting to the database: {e}")
                self.client.close()
                if attempt == retries:
                    raise e
                await asyncio.sleep(delay * 2 ** (attempt - 1))  # Exponential backoff

    async def disconnect(self):
        self.client.close()
        print("Disconnected from the database.")

    def get_database(self):
        return self.db


database_service = DatabaseService(DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME)


async def get_database_service():
    return database_service
