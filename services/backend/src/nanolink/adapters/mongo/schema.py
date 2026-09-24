from collections.abc import Sequence
from dataclasses import dataclass

from pymongo import ASCENDING, DESCENDING, IndexModel

from nanolink.adapters.mongo.connection import LINKS_COLLECTION, TASKS_COLLECTION, Document, MongoDatabase

TASK_RETENTION_SECONDS = 7 * 24 * 3600

LINKS_VALIDATOR: Document = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "short_code",
            "long_url",
            "owner_id",
            "task_id",
            "created_at",
            "updated_at",
            "deleted_at",
        ],
        "properties": {
            "short_code": {"bsonType": "string", "pattern": "^[0-9A-Za-z]{6}$"},
            "long_url": {"bsonType": "string", "minLength": 1, "maxLength": 2048},
            "owner_id": {"bsonType": "string", "pattern": "^[A-Za-z0-9_-]{1,64}$"},
            "task_id": {"bsonType": "string", "minLength": 1},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
            "deleted_at": {"bsonType": ["date", "null"]},
        },
    }
}

TASKS_VALIDATOR: Document = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["owner_id", "status", "created_at", "updated_at"],
        "properties": {
            "_id": {"bsonType": "string"},
            "owner_id": {"bsonType": "string"},
            "status": {"enum": ["queued", "created", "failed"]},
            "link_id": {"bsonType": ["string", "null"]},
            "failure": {"bsonType": ["string", "null"]},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}

LINK_INDEXES = [
    IndexModel([("short_code", ASCENDING)], name="short_code_unique", unique=True),
    IndexModel([("task_id", ASCENDING)], name="task_id_unique", unique=True),
    IndexModel(
        [("owner_id", ASCENDING), ("long_url", ASCENDING)],
        name="active_owner_long_url_unique",
        unique=True,
        partialFilterExpression={"deleted_at": {"$type": "null"}},
    ),
    IndexModel([("owner_id", ASCENDING), ("_id", DESCENDING)], name="owner_newest_first"),
]

TASK_INDEXES = [
    IndexModel([("owner_id", ASCENDING)], name="owner"),
    IndexModel(
        [("created_at", ASCENDING)], name="expire_after_retention", expireAfterSeconds=TASK_RETENTION_SECONDS
    ),
]


@dataclass(frozen=True, slots=True)
class DatabaseUser:
    name: str
    password: str
    role: str


async def migrate_database(database: MongoDatabase, users: Sequence[DatabaseUser]) -> None:
    await _ensure_collection(database, LINKS_COLLECTION, LINKS_VALIDATOR)
    await _ensure_collection(database, TASKS_COLLECTION, TASKS_VALIDATOR)
    await database[LINKS_COLLECTION].create_indexes(LINK_INDEXES)
    await database[TASKS_COLLECTION].create_indexes(TASK_INDEXES)
    await _ensure_users(database, users)


async def _ensure_collection(database: MongoDatabase, name: str, validator: Document) -> None:
    if name in await database.list_collection_names():
        await database.command("collMod", name, validator=validator, validationLevel="strict")
        return
    await database.create_collection(name, validator=validator, validationLevel="strict")


async def _ensure_users(database: MongoDatabase, users: Sequence[DatabaseUser]) -> None:
    existing = {entry["user"] for entry in (await database.command("usersInfo"))["users"]}
    for user in users:
        roles = [{"role": user.role, "db": database.name}]
        command = "updateUser" if user.name in existing else "createUser"
        await database.command(command, user.name, pwd=user.password, roles=roles)
