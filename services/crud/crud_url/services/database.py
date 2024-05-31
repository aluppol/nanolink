import os
from motor.motor_asyncio import AsyncIOMotorClient

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", 27017)
DB_NAME = os.getenv("DB_NAME")


class DatabaseService:
    def __init__(self, db_user: str, db_pass: str, db_host: str, db_port: str, db_name: str):
        # Construct the MongoDB URI
        db_uri = f"mongodb://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        self.client = AsyncIOMotorClient(db_uri)
        self.db = self.client[db_name]

    async def connect(self):
        try:
            await self.db.command("ping")
            print("Connected to the database successfully.")
        except Exception as e:
            print(f"Error connecting to the database: {e}")

    async def disconnect(self):
        self.client.close()
        print("Disconnected from the database.")

    def get_database(self):
        return self.db


database_service = DatabaseService(DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME)


async def get_database_service():
    return database_service
