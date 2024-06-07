import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", 27017)
DB_NAME = os.getenv("DB_NAME")


class DatabaseService:
    def __init__(
            self,
            db_user: str,
            db_pass: str,
            db_host: str,
            db_port: str,
            db_name: str,
            # maxPoolSize=None,
            # minPoolSize=None,
            # maxIdleTimeMS=None,
    ):
        self.__db_uri = f"mongodb://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        self.__db_name = db_name
        self.__client = None
        self.__db = None
        self.__check_connection_interval_s = 100    # seconds

        # connection pool config
        # self.__max_pool_size = maxPoolSize         # 100 if not set
        # self.__min_pool_size = minPoolSize         # 0 if not set
        # self.__max_idle_time_ms = maxIdleTimeMS    # 10s if not set

    async def connect(self):
        try:
            self.__client = AsyncIOMotorClient(
                self.__db_uri,
                # maxPoolSize=self.__max_pool_size,
                # minPoolSize=self.__min_pool_size,
                # maxIdleTimeMS=self.__max_idle_time_ms
            )
            self.__db = self.__client[self.__db_name]
            await self.__client.admin.command('ping')  # Check the connection
        except ConnectionFailure:
            self.__client = None
            self.__db = None
            raise ConnectionFailure("Database connection failed.")

    async def disconnect(self):
        self.__client.close()
        print("Disconnected from the database.")

    def get_database(self):
        return self.__db


database_service = DatabaseService(DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME)


async def get_database_service():
    return database_service
